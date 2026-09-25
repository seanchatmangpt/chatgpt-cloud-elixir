#!/usr/bin/env python3
"""Rail conformance court for the Chatman Ecosystem AGI Academy.

    python3 scripts/verify-agi-conformance.py [--receipt agi-conformance-receipt.json]

1. Structure (exit 2, REFUSED on any failure):
   - the vendored Academy files match their pinned digests;
   - the Academy manifest validates under the Academy's own verifier (reused, not re-implemented);
   - every Academy module, true invariant, and terminal refusal is mapped to at least one
     defined guard, and nothing unknown is mapped;
   - every failure-ledger entry is complete, names defined guards, and cites existing files.
2. Execution: every distinct guard runs once from the repository root. Standing comes only
   from exit codes: a mapping is ALIVE when all its guards exit 0, else BUILD_BROKEN.
3. Verdict: ALIVE (exit 0) only when every invariant, refusal, module, and ledger entry is
   ALIVE. Otherwise PARTIAL_ALIVE (exit 3). This mirrors the Academy verifier's exit semantics.

This court certifies nothing about any candidate and grants no authority (see non_claims).
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import platform
import subprocess
import sys
import time
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFORMANCE = ROOT / "governance" / "agi-academy-conformance.toml"
LEDGER_FIELDS = ("id", "observed", "failed_transition", "classification", "repair", "guards", "refs")


def refuse(errors: list[str]) -> int:
    for error in errors:
        print(f"REFUSED:{error}")
    return 2


def load_academy_verifier(path: Path):
    spec = importlib.util.spec_from_file_location("vendored_verify_agi_academy", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def structural_errors(conf: dict, manifest: dict, provenance: dict, provenance_dir: Path, ledger: dict, verifier) -> list[str]:
    errors = [f"ACADEMY_MANIFEST_INVALID:{e}" for e in verifier.validate_manifest(manifest)]
    for item in provenance.get("file", []):
        digest = hashlib.sha256((provenance_dir / item["path"]).read_bytes()).hexdigest()
        if digest != item["sha256"]:
            errors.append(f"VENDORED_DIGEST_DRIFT:{item['path']}")
    if manifest.get("release") != provenance.get("academy_release"):
        errors.append("ACADEMY_RELEASE_DRIFT: manifest release differs from PROVENANCE academy_release")

    guards = conf.get("guards", {})
    for gid, guard in guards.items():
        if not guard.get("command") or not guard.get("proves"):
            errors.append(f"GUARD_INCOMPLETE:{gid}")

    expected = {
        "modules": {m["id"] for m in manifest.get("module", [])},
        "invariants": {k for k, v in manifest.get("invariants", {}).items() if v is True},
        "refusals": set(manifest.get("invariants", {}).get("terminal_refusals", [])),
    }
    for section, required in expected.items():
        mapped = conf.get(section, {})
        for missing in sorted(required - set(mapped)):
            errors.append(f"UNMAPPED_{section.upper()}:{missing}")
        for unknown in sorted(set(mapped) - required):
            errors.append(f"UNKNOWN_{section.upper()}:{unknown}")
        for key, entry in mapped.items():
            if not entry.get("guards"):
                errors.append(f"UNGUARDED:{section}.{key}")
            if not entry.get("mechanism"):
                errors.append(f"UNEXPLAINED:{section}.{key}")
            for gid in entry.get("guards", []):
                if gid not in guards:
                    errors.append(f"UNKNOWN_GUARD:{section}.{key}->{gid}")

    ids = set()
    for entry in ledger.get("failure", []):
        fid = entry.get("id", "<missing id>")
        if fid in ids:
            errors.append(f"LEDGER_DUPLICATE:{fid}")
        ids.add(fid)
        for field in LEDGER_FIELDS:
            if not entry.get(field):
                errors.append(f"LEDGER_INCOMPLETE:{fid}.{field}")
        for gid in entry.get("guards", []):
            if gid not in guards:
                errors.append(f"LEDGER_UNKNOWN_GUARD:{fid}->{gid}")
        for ref in entry.get("refs", []):
            if not (ROOT / ref).exists():
                errors.append(f"LEDGER_REF_MISSING:{fid}->{ref}")
    return errors


def run_guard(command: str, timeout: int) -> dict:
    started = time.monotonic()
    try:
        proc = subprocess.run(["bash", "-c", command], cwd=ROOT, capture_output=True, text=True, timeout=timeout)
        code, tail = proc.returncode, (proc.stdout + proc.stderr).strip().splitlines()[-1:]
    except subprocess.TimeoutExpired:
        code, tail = 124, [f"timeout after {timeout}s"]
    return {"command": command, "exit": code, "seconds": round(time.monotonic() - started, 2), "tail": tail}


def git(*args: str) -> str | None:
    proc = subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True)
    return proc.stdout.strip() if proc.returncode == 0 else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--conformance", type=Path, default=DEFAULT_CONFORMANCE)
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--timeout", type=int, default=900)
    args = parser.parse_args()

    conf = tomllib.loads(args.conformance.read_text())
    manifest_path = ROOT / conf["academy_manifest"]
    provenance_path = ROOT / conf["academy_provenance"]
    manifest = tomllib.loads(manifest_path.read_text())
    provenance = tomllib.loads(provenance_path.read_text())
    ledger = tomllib.loads((ROOT / conf["failure_ledger"]).read_text())
    verifier = load_academy_verifier(provenance_path.parent / "verify_agi_academy.py")

    errors = structural_errors(conf, manifest, provenance, provenance_path.parent, ledger, verifier)
    if errors:
        return refuse(errors)

    results = {gid: run_guard(guard["command"], args.timeout) for gid, guard in conf["guards"].items()}

    def standing(guard_ids: list[str]) -> str:
        return "ALIVE" if all(results[g]["exit"] == 0 for g in guard_ids) else "BUILD_BROKEN"

    sections = {name: {k: standing(v["guards"]) for k, v in conf[name].items()} for name in ("invariants", "refusals", "modules")}
    ledger_standing = {e["id"]: standing(e["guards"]) for e in ledger.get("failure", [])}
    everything = [s for section in sections.values() for s in section.values()] + list(ledger_standing.values())
    verdict = "ALIVE" if all(s == "ALIVE" for s in everything) else "PARTIAL_ALIVE"

    receipt = {
        "schema": "chatgpt-cloud.agi-academy-rail-conformance-receipt.v1",
        "rail": {"repository": conf["rail"], "sha": git("rev-parse", "HEAD"),
                 "worktree_dirty": bool(git("status", "--porcelain")), "role": conf["role"]},
        "academy": {"release": manifest["release"], "source_repository": provenance["source_repository"],
                    "source_sha": provenance["source_sha"],
                    "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest()},
        "environment": {"platform": platform.platform(), "python": platform.python_version()},
        "guards": results,
        **sections,
        "failure_ledger": ledger_standing,
        "standing": verdict,
        "non_claims": conf["non_claims"],
        "observed_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "replay": "python3 scripts/verify-agi-conformance.py",
    }
    if args.receipt:
        args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")

    for gid, result in results.items():
        print(f"{'PASS' if result['exit'] == 0 else 'FAIL':<5} guard {gid:<20} exit={result['exit']} {result['seconds']}s")
    for name, section in sections.items():
        bad = sorted(k for k, s in section.items() if s != "ALIVE")
        print(f"{name:<11} {len(section) - len(bad)}/{len(section)} ALIVE" + (f"  broken: {', '.join(bad)}" if bad else ""))
    bad_ledger = sorted(k for k, s in ledger_standing.items() if s != "ALIVE")
    print(f"{'ledger':<11} {len(ledger_standing) - len(bad_ledger)}/{len(ledger_standing)} ALIVE" + (f"  broken: {', '.join(bad_ledger)}" if bad_ledger else ""))
    print(f"AGI_ACADEMY_RAIL_CONFORMANCE={verdict} academy={manifest['release']} rail_sha={receipt['rail']['sha']} dirty={receipt['rail']['worktree_dirty']}")
    return 0 if verdict == "ALIVE" else 3


if __name__ == "__main__":
    sys.exit(main())
