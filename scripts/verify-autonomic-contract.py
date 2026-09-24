#!/usr/bin/env python3
"""Bootstrap court for the autonomic manufacturing contract.

This verifier is intentionally dependency-free and narrow: it validates the source
identities and authority ceiling needed before ggen itself can be built. Semantic
projection is then delegated to the real pinned ggen binary.

The release identity is read from versions.toml and must agree with every other
surface that carries it (ontology, ggen.toml, CalVer date). The admitted source set
is enumerated twice, in the ontology and in capsules/autonomic-manufacturing/
capsule.toml `required_sources`; the two must be identical, and the manufacturing
core may never be dropped.
"""
from __future__ import annotations

import datetime as dt
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSIONS = ROOT / "versions.toml"
ONTOLOGY = ROOT / "manufacturing" / "ontology.ttl"
GGEN = ROOT / "manufacturing" / "ggen.toml"
CAPSULE = ROOT / "capsules" / "autonomic-manufacturing" / "capsule.toml"
OWNER = "seanchatmangpt"
BOOTSTRAP_TOOLCHAIN = "nightly-2026-06-22"
# The v26.8.25 manufacturing core. Growth is admitted; loss of the core is drift.
CORE_SOURCES = {
    "ggen",
    "ggen-marketplace",
    "ggen-create",
    "ggen-legacy",
    "ggen-spec-kit",
    "swarmsh",
    "swarmsh-v2",
}
# Current strategic portfolio closure. These are not manufacturing bootstrap roots, but
# they carry live ecosystem semantics that this rail must preserve once admitted.
STRATEGIC_SOURCES = {
    "engineering-standards",
    "zcode-cli",
    "rust4pm",
    "ash_kudzu",
    "koala-planner",
    "zoela",
    "mmdio",
}
# source-snapshot ships as an archive; source-reference is bound by exact commit + tree
# identity only (for members whose tree is dominated by non-executable corpora).
EXECUTION_MODES = {"compiled-binary", "source-snapshot", "source-reference", "shell-source", "typed-source"}
SOURCE_RE = re.compile(r"^cc:(\w+)\s+a\s+cc:CapabilitySource\s*;(.*?)\s\.[ \t]*$", re.S | re.M)
INCLUDES_RE = re.compile(r"cc:includesSource\s+(.*?)\s\.[ \t]*$", re.S | re.M)


def refuse(message: str) -> None:
    print(f"REFUSED_AUTONOMIC_CONTRACT: {message}", file=sys.stderr)
    raise SystemExit(65)


def literal(body: str, predicate: str) -> str | None:
    match = re.search(predicate + r'\s+"([^"]*)"', body)
    return match.group(1) if match else None


def main() -> int:
    versions = tomllib.loads(VERSIONS.read_text())
    release = versions.get("release", {}).get("version")
    if not isinstance(release, str) or not re.fullmatch(r"\d{2}\.\d{1,2}\.\d{1,2}", release):
        refuse("release.version must be YY.M.D CalVer")
    yy, month, day = (int(part) for part in release.split("."))
    if versions.get("release", {}).get("date") != dt.date(2000 + yy, month, day).isoformat():
        refuse(f"release.date must be the CalVer date of {release}")

    ontology = ONTOLOGY.read_text()
    if f'cc:releaseVersion "{release}"' not in ontology:
        refuse("ontology release identity drift")
    if "cc:authorityCeiling cc:CONSTRUCT_VERIFY" not in ontology:
        refuse("authority ceiling must remain CONSTRUCT_VERIFY")
    if "cc:requiresExternalExecution true" not in ontology:
        refuse("external execution boundary is missing")
    if "cc:privateIdentityProjection false" not in ontology:
        refuse("private identity projection fence is missing")
    if 'cc:lfsObjectPolicy "pointer-identity"' not in ontology:
        refuse('Git LFS law missing: capsule must declare cc:lfsObjectPolicy "pointer-identity"')
    for forbidden in ("DO_AUTHORITY", "AMBIENT_DO", "doAuthority true", "selfCertificationAllowed true"):
        if forbidden in ontology:
            refuse(f"forbidden authority token present: {forbidden}")

    found: dict[str, dict[str, str]] = {}
    locals_: dict[str, str] = {}
    repositories: set[str] = set()
    for local, body in SOURCE_RE.findall(ontology):
        fields = {
            key: literal(body, pred)
            for key, pred in (
                ("name", "skos:prefLabel"),
                ("repository", "cc:repository"),
                ("sha", "cc:commitSha"),
                ("mode", "cc:executionMode"),
                ("role", "cc:role"),
                ("capital", "cc:capitalClass"),
                ("standing", "cc:requiredStanding"),
                ("basis", "cc:admissionBasis"),
            )
        }
        missing = sorted(k for k, v in fields.items() if not v)
        if missing:
            refuse(f"source cc:{local} lacks {', '.join(missing)}")
        name = fields["name"]
        if name in found:
            refuse(f"duplicate source label: {name}")
        if not re.fullmatch(r"[0-9a-f]{40}", fields["sha"]):
            refuse(f"source {name} commitSha is not an exact 40-hex SHA")
        if fields["repository"] != f"{OWNER}/{name}":
            refuse(f"source {name} repository must be {OWNER}/{name}, got {fields['repository']}")
        if f"dcterms:source <https://github.com/{fields['repository']}>" not in body:
            refuse(f"source {name} dcterms:source does not match its repository")
        if fields["repository"] in repositories:
            refuse(f"duplicate source repository: {fields['repository']}")
        if fields["mode"] not in EXECUTION_MODES:
            refuse(f"source {name} has unknown executionMode {fields['mode']}")
        repositories.add(fields["repository"])
        locals_[local] = name
        found[name] = fields

    includes = INCLUDES_RE.search(ontology)
    if not includes:
        refuse("capsule does not declare cc:includesSource")
    included = re.findall(r"cc:(\w+)", includes.group(1))
    if len(included) != len(set(included)):
        refuse("cc:includesSource lists a source twice")
    if set(included) != set(locals_):
        refuse(
            "cc:includesSource and declared sources differ: "
            f"only-included={sorted(set(included) - set(locals_))} "
            f"only-declared={sorted(set(locals_) - set(included))}"
        )

    capsule = tomllib.loads(CAPSULE.read_text())
    required = capsule.get("required_sources", [])
    if len(required) != len(set(required)):
        refuse("capsule.toml required_sources lists a source twice")
    if set(found) != set(required):
        refuse(
            "source set drift between ontology and capsule.toml: "
            f"only-ontology={sorted(set(found) - set(required))} "
            f"only-capsule={sorted(set(required) - set(found))}"
        )
    if not CORE_SOURCES <= set(found):
        refuse(f"manufacturing core dropped: {sorted(CORE_SOURCES - set(found))}")
    if not STRATEGIC_SOURCES <= set(found):
        refuse(f"strategic portfolio source dropped: {sorted(STRATEGIC_SOURCES - set(found))}")
    if found["ggen"]["mode"] != "compiled-binary":
        refuse("ggen must remain the compiled-binary manufacturing runtime")

    bootstrap = versions.get("bootstrap", {})
    ggen = found["ggen"]
    if bootstrap.get("ggen_repository") != ggen["repository"]:
        refuse("bootstrap ggen repository differs from admitted ontology")
    if bootstrap.get("ggen_sha") != ggen["sha"]:
        refuse("bootstrap ggen SHA differs from admitted ontology")
    if bootstrap.get("rust_toolchain") != BOOTSTRAP_TOOLCHAIN:
        refuse(f"ggen bootstrap must use its pinned {BOOTSTRAP_TOOLCHAIN} toolchain")

    config = tomllib.loads(GGEN.read_text())
    if config.get("project", {}).get("version") != release:
        refuse("manufacturing/ggen.toml project.version differs from release")
    rules = config.get("generation", {}).get("rules", [])
    names = {r.get("name") for r in rules}
    if names != {"capability-lock", "manufacturing-topology"}:
        refuse(f"unexpected ggen projection set: {sorted(names)}")

    print(
        "AUTONOMIC_CONTRACT=ALIVE "
        f"release={release} sources={len(found)} authority=CONSTRUCT_VERIFY "
        f"ggen={ggen['sha']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
