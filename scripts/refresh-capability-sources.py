#!/usr/bin/env python3
"""Re-resolve every admitted capability source against its live default-branch HEAD.

This is the SELECT step for keeping manufacturing/ontology.ttl current with the rest of
the seanchatmangpt ecosystem. It never adds or removes sources (admission stays a
reviewed edit of ontology.ttl + capsules/autonomic-manufacturing/capsule.toml); it only
reports and, with --write, re-pins the exact SHAs of already-admitted sources.

    python3 scripts/refresh-capability-sources.py            # report drift, exit 1 if any
    python3 scripts/refresh-capability-sources.py --write    # re-pin drifted sources
    python3 scripts/refresh-capability-sources.py --receipt refresh-receipt.json

Standing per source: CURRENT | DRIFT | BLOCKED. BLOCKED means the anonymous git read
failed (private, renamed, deleted, or no network); such a source is never silently
dropped or re-pinned. A ggen bump is refused unless the new ggen revision still pins
the bootstrap Rust toolchain recorded in versions.toml, because the bootstrap court
would otherwise admit a compiler the workflow cannot build.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import json
import os
import re
import subprocess
import sys
import tomllib
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ONTOLOGY = ROOT / "manufacturing" / "ontology.ttl"
VERSIONS = ROOT / "versions.toml"
SOURCE_RE = re.compile(r"^cc:(\w+)\s+a\s+cc:CapabilitySource\s*;(.*?)\s\.[ \t]*$", re.S | re.M)
SHA_RE = re.compile(r'(cc:commitSha\s+")([0-9a-f]{40})(")')


def admitted_sources(ontology: str) -> list[dict[str, str]]:
    rows = []
    for match in SOURCE_RE.finditer(ontology):
        body = match.group(2)
        name = re.search(r'skos:prefLabel\s+"([^"]+)"', body)
        repository = re.search(r'cc:repository\s+"([^"]+)"', body)
        sha = SHA_RE.search(body)
        if not (name and repository and sha):
            raise SystemExit(f"REFUSED: source cc:{match.group(1)} lacks label/repository/commitSha")
        rows.append({"local": match.group(1), "name": name.group(1), "repository": repository.group(1), "admitted_sha": sha.group(2)})
    return rows


def repin(ontology: str, local: str, new_sha: str) -> str:
    """Replace the commitSha inside exactly one cc:<local> CapabilitySource block."""
    for match in SOURCE_RE.finditer(ontology):
        if match.group(1) != local:
            continue
        start, end = match.span(2)
        body, count = SHA_RE.subn(lambda m: m.group(1) + new_sha + m.group(3), match.group(2))
        if count != 1:
            raise SystemExit(f"REFUSED: cc:{local} must carry exactly one commitSha")
        return ontology[:start] + body + ontology[end:]
    raise SystemExit(f"REFUSED: cc:{local} not found")


def live_head(repository: str, timeout: int) -> tuple[str | None, str]:
    try:
        proc = subprocess.run(
            ["git", "ls-remote", f"https://github.com/{repository}.git", "HEAD"],
            capture_output=True, text=True, timeout=timeout,
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
        )
    except subprocess.TimeoutExpired:
        return None, "timeout"
    line = proc.stdout.split("\n", 1)[0].split("\t")[0].strip()
    if proc.returncode == 0 and re.fullmatch(r"[0-9a-f]{40}", line):
        return line, ""
    return None, (proc.stderr.strip().splitlines() or ["no HEAD"])[-1]


def ggen_toolchain(sha: str, timeout: int) -> str | None:
    url = f"https://raw.githubusercontent.com/seanchatmangpt/ggen/{sha}/rust-toolchain.toml"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return tomllib.loads(response.read().decode()).get("toolchain", {}).get("channel")
    except Exception:  # noqa: BLE001 - any failure means the toolchain is unobserved
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--write", action="store_true", help="re-pin drifted sources in ontology.ttl")
    parser.add_argument("--receipt", type=Path, help="write a JSON observation receipt")
    parser.add_argument("--jobs", type=int, default=8)
    parser.add_argument("--timeout", type=int, default=60)
    args = parser.parse_args()

    ontology = ONTOLOGY.read_text()
    rows = admitted_sources(ontology)
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        heads = list(pool.map(lambda r: live_head(r["repository"], args.timeout), rows))
    for row, (live, error) in zip(rows, heads):
        row["live_sha"] = live
        if live is None:
            row["standing"], row["error"] = "BLOCKED", error
        else:
            row["standing"] = "CURRENT" if live == row["admitted_sha"] else "DRIFT"

    versions_text = VERSIONS.read_text()
    bootstrap = tomllib.loads(versions_text)["bootstrap"]
    for row in rows:
        if row["name"] == "ggen" and row["standing"] == "DRIFT":
            observed = ggen_toolchain(row["live_sha"], args.timeout)
            if observed != bootstrap["rust_toolchain"]:
                row["standing"] = "BLOCKED"
                row["error"] = (
                    f"ggen {row['live_sha']} pins toolchain {observed!r}, bootstrap expects "
                    f"{bootstrap['rust_toolchain']!r}; bump versions.toml and the bootstrap court deliberately"
                )

    width = max(len(r["name"]) for r in rows)
    for row in rows:
        detail = row["live_sha"] if row["standing"] == "DRIFT" else row.get("error", "")
        print(f"{row['standing']:<8} {row['name']:<{width}} {row['admitted_sha'][:12]} {detail}".rstrip())
    drift = [r for r in rows if r["standing"] == "DRIFT"]
    blocked = [r for r in rows if r["standing"] == "BLOCKED"]
    print(f"sources={len(rows)} current={len(rows) - len(drift) - len(blocked)} drift={len(drift)} blocked={len(blocked)}")

    if args.write and drift:
        for row in drift:
            ontology = repin(ontology, row["local"], row["live_sha"])
            if row["name"] == "ggen":
                versions_text, count = re.subn(
                    r'^(ggen_sha\s*=\s*")[0-9a-f]{40}(")', lambda m: m.group(1) + row["live_sha"] + m.group(2),
                    versions_text, flags=re.M,
                )
                if count != 1:
                    raise SystemExit("REFUSED: versions.toml must carry exactly one bootstrap ggen_sha")
        ONTOLOGY.write_text(ontology)
        VERSIONS.write_text(versions_text)
        print(f"re-pinned {len(drift)} source(s); run scripts/verify-autonomic-contract.py and regenerate the lock")

    if args.receipt:
        args.receipt.write_text(json.dumps({
            "schema_version": 1,
            "check": "capability_source_refresh",
            "observed_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "written": bool(args.write and drift),
            "sources": rows,
        }, indent=2, sort_keys=True) + "\n")

    if blocked:
        return 69
    return 0 if (args.write or not drift) else 1


if __name__ == "__main__":
    raise SystemExit(main())
