#!/usr/bin/env python3
"""Deterministic benchmark for the git-ref A2A bus (scripts/a2a.py).

Builds a real bare remote plus a real clone, seeds one agent with an N-message
hash chain in a single commit, then measures on the git transport:

- ``verify_chain``: pure-CPU chain verification throughput (messages/second);
- ``sync_cold``: first ``sync`` of a fresh transport (wall seconds and git processes);
- ``sync_warm``: a second ``sync`` with nothing new on the bus (git processes);
- ``sync_incremental``: ``sync`` after one new message (git processes).

Git process counts are the regression metric: they are exact and machine
independent, while wall time on a shared host is only recorded. The counter is a
real ``Git`` subclass that runs every command and counts it; nothing is faked.

    python3 scripts/bench_a2a.py --messages 300 [--module scripts/a2a.py] [--out receipt.json]
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import platform
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent


def load(module: Path) -> Any:
    spec = importlib.util.spec_from_file_location("a2a_bench_subject", module)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["a2a_bench_subject"] = mod
    spec.loader.exec_module(mod)
    mod.PUSH_BACKOFF = 0.0
    return mod


def sh(*args: str, cwd: Path) -> str:
    return subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def chain(a2a: Any, agent: str, n: int) -> list[dict[str, Any]]:
    msgs, prev = [], None
    for seq in range(n):
        msg = a2a.seal({"@context": a2a.CONTEXT, "type": "a2a:Message", "schema": a2a.SCHEMA, "from": agent,
                        "to": "*", "seq": seq, "prev": prev, "conversation": f"{agent}:{seq}",
                        "in_reply_to": None, "performative": "inform", "skill": None,
                        "parts": [{"kind": "text", "text": f"benchmark message {seq}"}],
                        "created_at": "2026-09-25T00:00:00Z"})
        msgs.append(msg)
        prev = msg["id"]
    return msgs


def run(module: Path, n: int) -> dict[str, Any]:
    a2a = load(module)

    class CountingGit(a2a.Git):
        calls = 0

        def run(self, *args: str, **kw: Any):  # type: ignore[override]
            CountingGit.calls += 1
            return super().run(*args, **kw)

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        remote = root / "remote.git"
        sh("git", "init", "--bare", "-q", "-b", "main", str(remote), cwd=root)
        seed = root / "seed"
        sh("git", "init", "-q", "-b", "main", str(seed), cwd=root)
        (seed / "README").write_text("seed\n")
        sh("git", "add", ".", cwd=seed)
        sh("git", "-c", "user.name=b", "-c", "user.email=b@b", "commit", "-qm", "seed", cwd=seed)
        sh("git", "push", "-q", str(remote), "main:main", cwd=seed)
        clone = root / "alpha"
        sh("git", "clone", "-q", str(remote), str(clone), cwd=root)
        sh("git", "checkout", "-qb", "claude/alpha", cwd=clone)

        writer = a2a.Agent(a2a.Git(clone, "origin"), "alpha", "claude/alpha", ["claude/*"])
        writer.init(["echo"])
        msgs = chain(a2a, "alpha", n)
        files = {a2a.outbox_path("alpha", m["seq"]): json.dumps(m, indent=2, sort_keys=True).encode() + b"\n"
                 for m in msgs}
        writer.git.publish("claude/alpha", "alpha", lambda base: (files, "bench seed", None))

        t0 = time.perf_counter()
        a2a.verify_chain("alpha", msgs)
        verify_s = time.perf_counter() - t0

        reader = a2a.Agent(CountingGit(clone, "origin"), "alpha", "claude/alpha", ["claude/*"])
        CountingGit.calls = 0
        t0 = time.perf_counter()
        cold = reader.sync()
        cold_s = time.perf_counter() - t0
        cold_calls = CountingGit.calls
        assert cold["alpha"]["standing"] == "ALIVE" and len(cold["alpha"]["messages"]) == n, cold["alpha"]

        CountingGit.calls = 0
        t0 = time.perf_counter()
        reader.sync()
        warm_s = time.perf_counter() - t0
        warm_calls = CountingGit.calls

        writer.send("*", "inform", [{"kind": "text", "text": "one more"}])
        CountingGit.calls = 0
        t0 = time.perf_counter()
        inc = reader.sync()
        inc_s = time.perf_counter() - t0
        inc_calls = CountingGit.calls
        assert len(inc["alpha"]["messages"]) == n + 1

    return {
        "messages": n,
        "verify_chain": {"seconds": round(verify_s, 6), "messages_per_second": round(n / verify_s) if verify_s else None},
        "sync_cold": {"seconds": round(cold_s, 4), "git_processes": cold_calls},
        "sync_warm": {"seconds": round(warm_s, 4), "git_processes": warm_calls},
        "sync_incremental": {"seconds": round(inc_s, 4), "git_processes": inc_calls},
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--messages", type=int, default=300)
    ap.add_argument("--module", type=Path, default=HERE / "a2a.py")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args(argv)
    result = {
        "schema": "chatgpt-cloud-a2a-bench/v1",
        "module": str(args.module),
        "host": {"platform": platform.platform(), "python": platform.python_version(),
                 "git": sh("git", "--version", cwd=HERE)},
        **run(args.module, args.messages),
    }
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.out:
        args.out.write_text(text + "\n")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
