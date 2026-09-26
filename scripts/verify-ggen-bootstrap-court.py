#!/usr/bin/env python3
"""Executable admission court for exact GGen bootstrap observations."""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path, PurePosixPath

FIXTURES = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "ggen-bootstrap"

def admitted(rule: dict, value) -> bool:
    kind = rule["kind"]
    if kind == "exact":
        return value == rule["value"]
    if kind == "regex":
        return isinstance(value, str) and re.fullmatch(rule["pattern"], value) is not None
    if kind == "not_in":
        return value not in rule["values"]
    if kind == "nonempty":
        return isinstance(value, str) and bool(value.strip())
    if kind == "https_prefix":
        return isinstance(value, str) and value.startswith(rule["prefix"])
    if kind == "relative_path":
        if not isinstance(value, str) or not value:
            return False
        path = PurePosixPath(value)
        return not path.is_absolute() and ".." not in path.parts
    if kind == "true":
        return value is True
    if kind == "zero":
        return value == 0
    if kind == "min_int":
        return isinstance(value, int) and not isinstance(value, bool) and value >= rule["value"]
    if kind == "max_int":
        return isinstance(value, int) and not isinstance(value, bool) and value <= rule["value"]
    if kind == "allowed":
        return value in rule["values"]
    raise ValueError(f"unknown rule kind: {kind}")

def standing(rule: dict, value) -> str:
    return "ALIVE" if admitted(rule, value) else rule["failure_standing"]

def main() -> int:
    paths = sorted(FIXTURES.glob("p*.json"))
    if not paths:
        raise SystemExit("BUILD_BROKEN:NO_BOOTSTRAP_FIXTURES")
    ids, edges, fingerprints = set(), set(), set()
    for path in paths:
        case = json.loads(path.read_text(encoding="utf-8"))
        for key, seen in (("id", ids), ("edge", edges), ("semantic_fingerprint", fingerprints)):
            value = case[key]
            if value in seen:
                raise SystemExit(f"BUILD_BROKEN:DUPLICATE_{key.upper()}:{value}")
            seen.add(value)
        rule = case["rule"]
        probe = case["probe"]
        control = case["control"]
        observed_probe = standing(rule, probe["value"])
        if observed_probe != probe["expected_standing"]:
            raise SystemExit(
                f"BUILD_BROKEN:PROBE_STANDING:{case['id']}:{observed_probe}:"
                f"expected={probe['expected_standing']}"
            )
        observed_control = standing(rule, control["value"])
        if observed_control != "ALIVE" or control["expected_standing"] != "ALIVE":
            raise SystemExit(
                f"BUILD_BROKEN:CONTROL_NOT_ALIVE:{case['id']}:{observed_control}"
            )
    print(f"GGEN_BOOTSTRAP_COURT: ALIVE ({len(paths)} negative/control pairs)")
    return 0

if __name__ == "__main__":
    sys.exit(main())
