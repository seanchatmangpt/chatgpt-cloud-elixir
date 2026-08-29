#!/usr/bin/env python3
"""Cross-validate capsules/*/capsule.toml package sets against versions.toml and
each other.

This closes ERRC backlog item 28 (docs/errc-tracker.md CREATE #28 /
docs/errc-8020-vital-few.md §2 CREATE): "No script cross-validates
capsules/*/capsule.toml package sets stay consistent with each other or with
versions.toml." Static, offline, no Elixir/network required -- only reads
already-committed TOML.

Checks (each capsule.toml under capsules/*/capsule.toml):
  1. Every name in `packages` is a key under versions.toml's [packages] table.
  2. `packages` and `required_modules` (when both present) are the same length --
     a weak but cheap signal that a capsule wasn't updated on only one side.
  3. `fixture` (when present) names a directory that exists under fixtures/.
  4. Ash capsule package sets nest correctly: ash-core's packages must be a
     subset of ash-postgres's, ash-phoenix's, and ash-full's; ash-postgres's and
     ash-phoenix's must each be a subset of ash-full's (ash-full is documented as
     "maximal admitted compatible Ash ecosystem closure").
  5. postgres17's `version_key` names a key under versions.toml's [services].

Exit code 0 and "CAPSULE_PACKAGE_CONSISTENCY=ALIVE" iff every capsule passes every
applicable check. Otherwise prints one "BUILD_BROKEN: ..." line per violation to
stderr and exits 65, matching this repo's other verify-*.py exit conventions
(see scripts/verify-autonomic-contract.py, scripts/verify-release.py).
"""
from __future__ import annotations

import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NESTING = {
    # smaller capsule name -> capsule(s) whose package set it must be a subset of
    "ash-core": ["ash-postgres", "ash-phoenix", "ash-full"],
    "ash-postgres": ["ash-full"],
    "ash-phoenix": ["ash-full"],
}


def load_toml(path: Path) -> dict:
    return tomllib.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    problems: list[str] = []

    versions = load_toml(ROOT / "versions.toml")
    known_packages = set(versions.get("packages", {}))
    known_services = set(versions.get("services", {}))

    capsule_paths = sorted((ROOT / "capsules").glob("*/capsule.toml"))
    if not capsule_paths:
        problems.append(f"no capsules/*/capsule.toml found under {ROOT / 'capsules'}")

    capsules: dict[str, dict] = {}
    for path in capsule_paths:
        cfg = load_toml(path)
        name = cfg.get("name", path.parent.name)
        capsules[name] = cfg

        for pkg in cfg.get("packages", []):
            if pkg not in known_packages:
                problems.append(
                    f"{path.relative_to(ROOT)}: packages entry '{pkg}' has no matching "
                    f"key under versions.toml [packages]"
                )

        packages = cfg.get("packages", [])
        required_modules = cfg.get("required_modules", [])
        if packages or required_modules:
            if len(packages) != len(required_modules):
                problems.append(
                    f"{path.relative_to(ROOT)}: packages has {len(packages)} entries but "
                    f"required_modules has {len(required_modules)} -- likely edited on only "
                    f"one side"
                )

        fixture = cfg.get("fixture")
        if fixture is not None and not (ROOT / "fixtures" / fixture).is_dir():
            problems.append(
                f"{path.relative_to(ROOT)}: fixture = '{fixture}' has no matching "
                f"directory under fixtures/"
            )

        if name == "postgres17":
            version_key = cfg.get("version_key")
            if version_key is not None and version_key not in known_services:
                problems.append(
                    f"{path.relative_to(ROOT)}: version_key = '{version_key}' has no "
                    f"matching key under versions.toml [services]"
                )

    for smaller, largers in NESTING.items():
        if smaller not in capsules:
            continue
        smaller_pkgs = set(capsules[smaller].get("packages", []))
        for larger in largers:
            if larger not in capsules:
                continue
            larger_pkgs = set(capsules[larger].get("packages", []))
            missing = smaller_pkgs - larger_pkgs
            if missing:
                problems.append(
                    f"capsules/{smaller}/capsule.toml: packages {sorted(missing)} are not "
                    f"present in capsules/{larger}/capsule.toml, but {smaller} is expected "
                    f"to be a subset of {larger}"
                )

    if problems:
        for problem in problems:
            print(f"BUILD_BROKEN: {problem}", file=sys.stderr)
        return 65

    print(
        f"CAPSULE_PACKAGE_CONSISTENCY=ALIVE capsules={len(capsules)} "
        f"known_packages={len(known_packages)} known_services={len(known_services)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
