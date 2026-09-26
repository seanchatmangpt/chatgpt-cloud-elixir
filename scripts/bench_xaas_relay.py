#!/usr/bin/env python3
"""Deterministic benchmark for the XaaS relay worker (scripts/xaas-relay.py).

Real collaborators: the relay module from disk, a real state file, and a real
gall-work peer executable that counts its own spawns in a file. Measures:

- ``admission``: validate_envelope throughput (envelopes/second, CPU only);
- ``duplicate_delivery``: one fresh command then D identical redeliveries;
  exact metric = peer spawns (must be 1), plus median replay latency;
- ``refusal``: SEQUENCE_GAP / REPLAY_IDENTITY_MISMATCH refusal latency with
  exact metric = spawns (must stay unchanged);
- ``ordered_stream``: M sequential commands with dedup_limit K; exact metrics =
  spawns (M), persisted result rows (K) and state bytes per row.

Exact counts are the regression metric (machine independent); wall times are
recorded for the receipt and only guarded by order-of-magnitude floors.

    python3 scripts/bench_xaas_relay.py [--commands 40] [--duplicates 200] [--out receipt.json]
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import platform
import stat
import statistics
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
EPOCH = "11111111-1111-4111-8111-111111111111"
PEER = (
    "#!/usr/bin/env python3\n"
    "import json, os, pathlib\n"
    "p=pathlib.Path(os.environ['COUNTER'])\n"
    "p.write_text(str(int(p.read_text())+1 if p.exists() else 1))\n"
    "print(json.dumps({'schema':'gall.work-result/1','standing':'ALIVE','epoch_id':os.environ['XAAS_EPOCH_ID'],"
    "'outcome':'alive','final_head':'c'*40,'runtime_exit_code':0,"
    "'work_order_iri':os.environ['XAAS_WORK_ORDER_IRI'],'base_sha':os.environ['XAAS_BASE_SHA']}))\n"
)


def load(module: Path) -> Any:
    spec = importlib.util.spec_from_file_location("xaas_relay_bench_subject", module)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def descriptor(worktree: Path, **overrides: Any) -> dict[str, Any]:
    value = {
        "schema": "gall.work-lease/1",
        "work_order_iri": "urn:work:bench",
        "checkpoint_iri": "urn:checkpoint:bench",
        "graph_digest": "sha256:" + "b" * 64,
        "repository_identity": "owner/repo",
        "base_sha": "a" * 40,
        "epoch_id": EPOCH,
        "worker_id": "bench-worker",
        "worktree": str(worktree),
    }
    value.update(overrides)
    return value


def envelope(d: dict[str, Any], command_id: str, sequence: int) -> dict[str, Any]:
    return {
        "schema": "xaas.remote-relay-envelope/1",
        "command_id": command_id,
        "epoch_id": d["epoch_id"],
        "task_id": d["work_order_iri"],
        "sequence": sequence,
        "intent_digest": d["graph_digest"],
        "exact_subject": f"{d['repository_identity']}@{d['base_sha']}",
        "verb": "actuate",
        "expires_at": 2 ** 62,
        "execution_manifest_digest": "bench-manifest",
        "authority_ref": "bench-grant",
        "channel": "control",
        "payload": d,
    }


class Rig:
    def __init__(self, relay: Any, root: Path, name: str) -> None:
        self.relay = relay
        self.root = root / name
        self.worktree = self.root / "worktree"
        self.worktree.mkdir(parents=True)
        self.state = self.root / "state.json"
        self.counter = self.root / "count.txt"
        self.peer = self.root / "zcode"
        self.peer.write_text(PEER)
        self.peer.chmod(self.peer.stat().st_mode | stat.S_IXUSR)
        self.env = dict(os.environ, COUNTER=str(self.counter))

    def spawns(self) -> int:
        return int(self.counter.read_text()) if self.counter.exists() else 0

    def deliver(self, env_doc: dict[str, Any], dedup_limit: int = 256) -> tuple[dict[str, Any], float]:
        start = time.perf_counter()
        row = self.relay.run_envelope(env_doc, state_path=self.state, manifest_digest="bench-manifest",
                                      zcode=str(self.peer), allow_do=True, env=self.env,
                                      dedup_limit=dedup_limit, now_ms=1)
        return row, time.perf_counter() - start


def run(module: Path, commands: int = 40, duplicates: int = 200, dedup_limit: int = 8,
        admissions: int = 20000) -> dict[str, Any]:
    relay = load(module)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        out: dict[str, Any] = {}

        wt = root / "wt"
        wt.mkdir()
        doc = envelope(descriptor(wt), "cmd-admit", 1)
        start = time.perf_counter()
        for _ in range(admissions):
            relay.validate_envelope(doc, manifest_digest="bench-manifest", now_ms=1)
        elapsed = time.perf_counter() - start
        out["admission"] = {"envelopes": admissions, "seconds": elapsed,
                            "envelopes_per_second": admissions / elapsed}

        rig = Rig(relay, root, "dup")
        d = descriptor(rig.worktree)
        first, first_s = rig.deliver(envelope(d, "cmd-1", 1))
        replay_times, reasons = [], set()
        for _ in range(duplicates):
            row, secs = rig.deliver(envelope(d, "cmd-1", 1))
            replay_times.append(secs)
            reasons.add(row["reason"])
        out["duplicate_delivery"] = {
            "first_reason": first["reason"], "first_seconds": first_s,
            "redeliveries": duplicates, "replay_reasons": sorted(reasons),
            "spawns": rig.spawns(),
            "replay_median_seconds": statistics.median(replay_times),
            "replay_p95_seconds": sorted(replay_times)[int(0.95 * (len(replay_times) - 1))],
        }

        forged = descriptor(rig.worktree, base_sha="d" * 40, graph_digest="sha256:" + "e" * 64)
        mismatch_times, gap_times, refusal_reasons = [], [], set()
        for _ in range(duplicates):
            row, secs = rig.deliver(envelope(forged, "cmd-1", 1))
            mismatch_times.append(secs)
            refusal_reasons.add(row["reason"])
            row, secs = rig.deliver(envelope(d, "cmd-gap", 5))
            gap_times.append(secs)
            refusal_reasons.add(row["reason"])
        out["refusal"] = {
            "attempts": 2 * duplicates, "reasons": sorted(refusal_reasons),
            "spawns_after": rig.spawns(),
            "identity_mismatch_median_seconds": statistics.median(mismatch_times),
            "sequence_gap_median_seconds": statistics.median(gap_times),
        }

        rig = Rig(relay, root, "stream")
        d = descriptor(rig.worktree)
        exec_times, reasons = [], set()
        for n in range(1, commands + 1):
            row, secs = rig.deliver(envelope(d, f"cmd-{n}", n), dedup_limit=dedup_limit)
            exec_times.append(secs)
            reasons.add(row["reason"])
        state = json.loads(rig.state.read_text())
        size = rig.state.stat().st_size
        out["ordered_stream"] = {
            "commands": commands, "dedup_limit": dedup_limit, "reasons": sorted(reasons),
            "spawns": rig.spawns(), "result_rows": len(state["results"]),
            "seen_ids": len(state["seen_command_ids"]),
            "last_acknowledged_sequence": state["last_acknowledged_sequence"],
            "state_bytes": size,
            "execute_median_seconds": statistics.median(exec_times),
        }
        return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--module", type=Path, default=HERE / "xaas-relay.py")
    p.add_argument("--commands", type=int, default=40)
    p.add_argument("--duplicates", type=int, default=200)
    p.add_argument("--dedup-limit", type=int, default=8)
    p.add_argument("--out", type=Path)
    args = p.parse_args(argv)
    result = run(args.module, args.commands, args.duplicates, args.dedup_limit)
    receipt = {
        "schema": "chatgpt-cloud.xaas-relay-bench/1",
        "host": {"python": sys.version.split()[0], "platform": platform.platform(), "machine": platform.machine()},
        "parameters": {"commands": args.commands, "duplicates": args.duplicates, "dedup_limit": args.dedup_limit},
        "result": result,
    }
    text = json.dumps(receipt, indent=2, sort_keys=True)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
