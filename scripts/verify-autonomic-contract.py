#!/usr/bin/env python3
"""Bootstrap court for the v26.8.25 autonomic manufacturing contract.

This verifier is intentionally dependency-free and narrow: it validates the source
identities and authority ceiling needed before ggen itself can be built. Semantic
projection is then delegated to the real pinned ggen binary.
"""
from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSIONS = ROOT / "versions.toml"
ONTOLOGY = ROOT / "manufacturing" / "ontology.ttl"
GGEN = ROOT / "manufacturing" / "ggen.toml"
EXPECTED_RELEASE = "26.8.25"
EXPECTED_SOURCES = {
    "Ggen",
    "GgenMarketplace",
    "GgenCreate",
    "GgenLegacy",
    "GgenSpecKit",
    "SwarmSH",
    "SwarmSHV2",
}
SHA_RE = re.compile(r'cc:commitSha\s+"([0-9a-f]{40})"')
SOURCE_RE = re.compile(r"cc:(\w+)\s+a\s+cc:CapabilitySource\s*;(.*?)(?=\n\ncc:|\Z)", re.S)


def refuse(message: str) -> None:
    print(f"REFUSED_AUTONOMIC_CONTRACT: {message}", file=sys.stderr)
    raise SystemExit(65)


def main() -> int:
    versions = tomllib.loads(VERSIONS.read_text())
    if versions.get("release", {}).get("version") != EXPECTED_RELEASE:
        refuse("release.version must be 26.8.25")
    if versions.get("release", {}).get("date") != "2026-08-25":
        refuse("release.date must be 2026-08-25")

    ontology = ONTOLOGY.read_text()
    if 'cc:releaseVersion "26.8.25"' not in ontology:
        refuse("ontology release identity drift")
    if "cc:authorityCeiling cc:CONSTRUCT_VERIFY" not in ontology:
        refuse("authority ceiling must remain CONSTRUCT_VERIFY")
    if "cc:requiresExternalExecution true" not in ontology:
        refuse("external execution boundary is missing")
    for forbidden in ("DO_AUTHORITY", "AMBIENT_DO", "doAuthority true", "selfCertificationAllowed true"):
        if forbidden in ontology:
            refuse(f"forbidden authority token present: {forbidden}")

    found = {}
    for name, body in SOURCE_RE.findall(ontology):
        sha = SHA_RE.search(body)
        repo = re.search(r'cc:repository\s+"([^"]+)"', body)
        mode = re.search(r'cc:executionMode\s+"([^"]+)"', body)
        if not sha or not repo or not mode:
            refuse(f"source {name} lacks exact repository/sha/executionMode")
        found[name] = {"sha": sha.group(1), "repository": repo.group(1), "mode": mode.group(1)}

    if set(found) != EXPECTED_SOURCES:
        refuse(f"source set drift: expected {sorted(EXPECTED_SOURCES)}, got {sorted(found)}")

    bootstrap = versions.get("bootstrap", {})
    ggen = found["Ggen"]
    if bootstrap.get("ggen_repository") != ggen["repository"]:
        refuse("bootstrap ggen repository differs from admitted ontology")
    if bootstrap.get("ggen_sha") != ggen["sha"]:
        refuse("bootstrap ggen SHA differs from admitted ontology")
    if bootstrap.get("rust_toolchain") != "nightly-2026-06-22":
        refuse("ggen bootstrap must use its pinned nightly-2026-06-22 toolchain")

    config = tomllib.loads(GGEN.read_text())
    rules = config.get("generation", {}).get("rules", [])
    names = {r.get("name") for r in rules}
    if names != {"capability-lock", "manufacturing-topology"}:
        refuse(f"unexpected ggen projection set: {sorted(names)}")

    print(
        "AUTONOMIC_CONTRACT=ALIVE "
        f"release={EXPECTED_RELEASE} sources={len(found)} authority=CONSTRUCT_VERIFY "
        f"ggen={ggen['sha']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
