#!/usr/bin/env python3
"""Check every versions.toml package pin against the OSV advisory database.

Permanent guard for a failure observed on 2026-09-23: replaying the committed Hex cache
offline surfaced advisories against nine admitted Ash pins that nothing had flagged.
Routes the question to OSV (a known machine) instead of relying on someone noticing.

    python3 scripts/check-advisories.py                  # exit 0 clean, 1 advisories, 69 blocked
    python3 scripts/check-advisories.py --receipt advisories.json

Network is required: this guard runs in CI (advisory-watch.yml), never inside a capsule.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import tomllib
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSIONS = ROOT / "versions.toml"
OSV_BATCH = "https://api.osv.dev/v1/querybatch"


def pinned_packages(versions: dict) -> list[tuple[str, str]]:
    return sorted(versions.get("packages", {}).items())


def batch_query(pins: list[tuple[str, str]]) -> dict:
    return {"queries": [{"package": {"name": name, "ecosystem": "Hex"}, "version": version} for name, version in pins]}


def advisories_from_batch(pins: list[tuple[str, str]], response: dict) -> dict[str, list[str]]:
    """Map each pin to the advisory ids OSV reports for it (pure; no I/O)."""
    results = response.get("results", [])
    if len(results) != len(pins):
        raise ValueError(f"OSV returned {len(results)} results for {len(pins)} queries")
    return {
        f"{name}@{version}": sorted(v["id"] for v in (result.get("vulns") or []))
        for (name, version), result in zip(pins, results)
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--timeout", type=int, default=60)
    args = parser.parse_args()

    pins = pinned_packages(tomllib.loads(VERSIONS.read_text()))
    request = urllib.request.Request(OSV_BATCH, data=json.dumps(batch_query(pins)).encode(),
                                     headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=args.timeout) as handle:
            findings = advisories_from_batch(pins, json.load(handle))
        standing = "BUILD_BROKEN" if any(findings.values()) else "ALIVE"
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        findings, standing = {}, "BLOCKED"
        print(f"BLOCKED: OSV unreachable or malformed response: {exc}", file=sys.stderr)

    for pin, ids in findings.items():
        print(f"{'ADVISORY' if ids else 'CLEAN':<9} {pin:<36} {' '.join(ids)}".rstrip())
    print(f"ADVISORIES={standing} pins={len(pins)} affected={sum(1 for ids in findings.values() if ids)}")
    if args.receipt:
        args.receipt.write_text(json.dumps({
            "schema": "chatgpt-cloud.advisory-check.v1",
            "source": "versions.toml [packages]",
            "database": OSV_BATCH,
            "observed_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "findings": findings,
            "standing": standing,
        }, indent=2, sort_keys=True) + "\n")
    return {"ALIVE": 0, "BUILD_BROKEN": 1}.get(standing, 69)


if __name__ == "__main__":
    raise SystemExit(main())
