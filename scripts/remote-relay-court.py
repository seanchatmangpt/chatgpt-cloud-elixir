#!/usr/bin/env python3
"""Independent cross-repository court for the bounded XaaS remote relay."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_json(path: Path) -> tuple[bytes, dict[str, Any]]:
    raw = path.read_bytes()
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return raw, value


def check(
    local_contract: Path,
    xaas_contract: Path,
    zcode_contract: Path,
    zcode_ocel_source: Path,
) -> dict[str, Any]:
    local_raw, local = load_json(local_contract)
    xaas_raw, xaas = load_json(xaas_contract)
    zcode_raw, zcode = load_json(zcode_contract)
    zcode_ocel_raw = zcode_ocel_source.read_bytes()
    zcode_ocel_text = zcode_ocel_raw.decode("utf-8")

    checks = [
        {
            "id": "REMOTE_RELAY_BYTES_IDENTICAL",
            "alive": local_raw == xaas_raw,
            "detail": "cloud vendored contract is byte-identical to XaaS source contract",
        },
        {
            "id": "REMOTE_RELAY_SCHEMA_IDENTICAL",
            "alive": local.get("envelope_schema") == xaas.get("envelope_schema")
            == "xaas.remote-relay-envelope/1",
            "detail": "both sides admit the same envelope schema",
        },
        {
            "id": "GALL_DESCRIPTOR_SCHEMA_COMPOSES",
            "alive": local.get("gall_work_binding", {}).get("payload_schema")
            == zcode.get("command", {}).get("descriptor_schema")
            == "gall.work-lease/1",
            "detail": "relay payload schema equals zcode native lease schema",
        },
        {
            "id": "GALL_LEASE_ARGV_FIXED",
            "alive": zcode.get("command", {}).get("argv_lease_form")
            == ["gall-work", "--lease", "<descriptor.json>", "--json"],
            "detail": "the only worker consequence adapter remains the fixed gall-work lease command",
        },
        {
            "id": "OCEL_IDENTITY_ENV_COMPOSES",
            "alive": all(
                name in zcode_ocel_text
                for name in local.get("ocel_identity_env", [])
            )
            and local.get("ocel_identity_env")
            == [
                "XAAS_LEASE_CWD",
                "XAAS_WORK_ORDER_IRI",
                "XAAS_EPOCH_ID",
                "XAAS_BASE_SHA",
            ],
            "detail": "relay exports exactly the identity variables consumed by the zcode OCEL tap",
        },
        {
            "id": "AUTHORITY_CONSERVED",
            "alive": local.get("gall_work_binding", {}).get("local_do_ack", "").startswith(
                "worker must independently require explicit local allow-do"
            ),
            "detail": "relay authority reference is necessary but never sufficient for local DO",
        },
        {
            "id": "REPLAY_BOUND",
            "alive": "KNOWN_REPLAY" in local.get("replay", {}).get("after_ack", "")
            and "must not spawn zcode again" in local.get("replay", {}).get("consequence_bound", ""),
            "detail": "acknowledged duplicate delivery cannot become a second consequence",
        },
    ]

    standing = "ALIVE" if all(item["alive"] for item in checks) else "BUILD_BROKEN"
    return {
        "schema": "xaas.remote-relay-court/1",
        "standing": standing,
        "subjects": {
            "cloud_contract": {
                "path": str(local_contract),
                "sha256": sha256(local_raw),
            },
            "xaas_contract": {
                "path": str(xaas_contract),
                "sha256": sha256(xaas_raw),
            },
            "zcode_contract": {
                "path": str(zcode_contract),
                "sha256": sha256(zcode_raw),
            },
            "zcode_ocel_source": {
                "path": str(zcode_ocel_source),
                "sha256": sha256(zcode_ocel_raw),
            },
        },
        "checks": checks,
        "evidence_ceiling": (
            "cross-repository contract composition and repository-local tests; "
            "not deployment, host reachability, production authority, customer authority, or external standing"
        ),
    }


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--local-contract", type=Path, required=True)
    p.add_argument("--xaas-contract", type=Path, required=True)
    p.add_argument("--zcode-contract", type=Path, required=True)
    p.add_argument("--zcode-ocel-source", type=Path, required=True)
    p.add_argument("--receipt", type=Path)
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        receipt = check(
            args.local_contract,
            args.xaas_contract,
            args.zcode_contract,
            args.zcode_ocel_source,
        )
    except (OSError, ValueError, json.JSONDecodeError) as error:
        receipt = {
            "schema": "xaas.remote-relay-court/1",
            "standing": "BUILD_BROKEN",
            "error": f"{error.__class__.__name__}: {error}",
        }

    rendered = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(rendered)
    print(rendered, end="")
    return 0 if receipt["standing"] == "ALIVE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
