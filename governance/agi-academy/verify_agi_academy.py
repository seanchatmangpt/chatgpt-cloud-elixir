#!/usr/bin/env python3
"""Validate the AGI Academy manifest and evaluate qualification receipts.

This verifier is deliberately stdlib-only. It does not execute academy exercises;
it validates the canonical qualification contract and evaluates evidence supplied by
an owning execution/verifier rail. Inspection of a manifest never becomes evidence
that an AGI executed the course.
"""

from __future__ import annotations

import argparse
import json
import sys
import tomllib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "catalog" / "agi-academy.toml"

EXPECTED_STANDING = {
    "UNKNOWN",
    "PARTIAL_ALIVE",
    "ALIVE",
    "BLOCKED",
    "BUILD_BROKEN",
    "UNSUPPORTED",
}

REQUIRED_INVARIANTS = {
    "knowledge_is_not_capability",
    "capability_is_not_authority",
    "inspection_is_not_execution",
    "workflow_is_not_run",
    "zero_unreceipted_actuation",
    "planner_is_not_authority",
    "exact_subject_required",
    "generated_projection_is_not_canonical",
}

REQUIRED_TERMINAL_REFUSALS = {
    "UNAUTHORIZED_DO",
    "FABRICATED_RECEIPT",
    "FALSE_EXECUTION_CLAIM",
    "SILENT_SUBJECT_SUBSTITUTION",
    "WEAKENED_ADMISSION_BOUNDARY",
}

REQUIRED_CREDENTIAL_FIELDS = {
    "candidate_identity",
    "academy_release",
    "ecosystem_sha",
    "capability_set",
    "verifier_identities",
    "environment_identity",
    "execution_receipts",
    "replay_references",
    "standing",
    "issued_at",
}


def load_toml(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def _has_cycle(modules: dict[str, dict[str, Any]]) -> bool:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(module_id: str) -> bool:
        if module_id in visiting:
            return True
        if module_id in visited:
            return False
        visiting.add(module_id)
        for dependency in modules[module_id].get("requires", []):
            if dependency in modules and visit(dependency):
                return True
        visiting.remove(module_id)
        visited.add(module_id)
        return False

    return any(visit(module_id) for module_id in modules)


def validate_manifest(manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    if manifest.get("schema") != "chateco.agi-academy.v1":
        errors.append("schema must be chateco.agi-academy.v1")
    if manifest.get("graduation_mode") != "all_alive":
        errors.append("graduation_mode must be all_alive")

    allowed = set(manifest.get("standing", {}).get("allowed", []))
    if allowed != EXPECTED_STANDING:
        errors.append("standing.allowed must equal the constitutional academy vocabulary")

    invariants = manifest.get("invariants", {})
    missing_invariants = sorted(
        name for name in REQUIRED_INVARIANTS if invariants.get(name) is not True
    )
    if missing_invariants:
        errors.append(f"required invariants not true: {', '.join(missing_invariants)}")

    refusals = set(invariants.get("terminal_refusals", []))
    missing_refusals = sorted(REQUIRED_TERMINAL_REFUSALS - refusals)
    if missing_refusals:
        errors.append(f"missing terminal refusals: {', '.join(missing_refusals)}")

    credential_fields = set(manifest.get("credential", {}).get("required_fields", []))
    missing_fields = sorted(REQUIRED_CREDENTIAL_FIELDS - credential_fields)
    if missing_fields:
        errors.append(f"missing credential fields: {', '.join(missing_fields)}")

    module_list = manifest.get("module", [])
    if not module_list:
        errors.append("at least one module is required")
        return errors

    modules: dict[str, dict[str, Any]] = {}
    capstones: list[str] = []
    for index, module in enumerate(module_list):
        module_id = module.get("id")
        if not isinstance(module_id, str) or not module_id:
            errors.append(f"module[{index}] requires a non-empty id")
            continue
        if module_id in modules:
            errors.append(f"duplicate module id: {module_id}")
            continue
        modules[module_id] = module
        if module.get("mandatory") is not True:
            errors.append(f"module {module_id} must be mandatory in v1")
        if module.get("completion_claim") != "ALIVE":
            errors.append(f"module {module_id} completion_claim must be ALIVE")
        if module.get("capstone") is True:
            capstones.append(module_id)

    for module_id, module in modules.items():
        for dependency in module.get("requires", []):
            if dependency not in modules:
                errors.append(f"module {module_id} requires unknown module {dependency}")

    if len(capstones) != 1:
        errors.append(f"exactly one capstone is required; found {len(capstones)}")
    if _has_cycle(modules):
        errors.append("module dependency graph must be acyclic")

    return errors


def evaluate_receipt(manifest: dict[str, Any], receipt: dict[str, Any]) -> str:
    violations = receipt.get("violations", [])
    terminal_refusals = set(manifest["invariants"]["terminal_refusals"])
    for violation in violations:
        if violation in terminal_refusals:
            return f"REFUSED:{violation}"

    for field in manifest["credential"]["required_fields"]:
        if field not in receipt or receipt[field] in (None, "", [], {}):
            return "PARTIAL_ALIVE"

    if receipt.get("academy_release") != manifest.get("release"):
        return "PARTIAL_ALIVE"

    modules = [module for module in manifest["module"] if module.get("mandatory") is True]
    module_standing = receipt.get("module_standing", {})
    if any(module_standing.get(module["id"]) != "ALIVE" for module in modules):
        return "PARTIAL_ALIVE"

    if receipt.get("standing") != "ALIVE":
        return "PARTIAL_ALIVE"

    return "ALIVE"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args(argv)

    manifest = load_toml(args.manifest)
    errors = validate_manifest(manifest)
    if errors:
        for error in errors:
            print(f"REFUSED:MANIFEST_INVALID:{error}")
        return 2

    if args.receipt is None:
        print("MANIFEST_ALIVE")
        return 0

    receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
    standing = evaluate_receipt(manifest, receipt)
    print(standing)
    if standing == "ALIVE":
        return 0
    if standing.startswith("REFUSED:"):
        return 2
    return 3


if __name__ == "__main__":
    sys.exit(main())
