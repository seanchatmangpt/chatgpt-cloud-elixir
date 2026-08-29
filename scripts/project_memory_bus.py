#!/usr/bin/env python3
"""Fail-closed front controller for Project #2 memory requests.

This gate owns transport correctness only. The bounded Project-v2 mutation
semantics remain in ``project_memory_proxy.py``; read-only semantic and Vision
2030 projections are layered by ``project_memory_semantic_proxy.py``.

Invariants:
- malformed transport is REFUSED, never misclassified as proxy BUILD_BROKEN;
- exact successful requests are replay-idempotent and never actuate twice;
- receipts bind both raw transport bytes and canonical request semantics;
- GGEN Ecosystem OCEL claims have one canonical Project #2 key and contract;
- no credential is read before the request envelope is admitted.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any

BASE_PROXY_PATH = Path(__file__).with_name("project_memory_proxy.py")
SEMANTIC_PROXY_PATH = Path(__file__).with_name("project_memory_semantic_proxy.py")
GATE_SCHEMA = "chatgpt-project-memory-gate/v2"
GGEN_ECOSYSTEM_OCEL_KEY = "ggen/ecosystem/ocel/current"
GGEN_ECOSYSTEM_OCEL_KIND = "ggen.ecosystem.ocel.current"
GGEN_ECOSYSTEM_OCEL_TAGS = {"ggen", "ocel", "manufacturing", "project2"}


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_proxy():
    # Always load a fresh base before applying the semantic extension. This
    # prevents repeated in-process gate invocations from stacking wrappers.
    base = _load_module("project_memory_proxy", BASE_PROXY_PATH)
    semantic = _load_module("project_memory_semantic_proxy", SEMANTIC_PROXY_PATH)
    if semantic.base is not base:
        raise RuntimeError("semantic proxy did not bind the admitted base proxy")
    return base


def sha256_bytes(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def canonical_digest(request: dict[str, Any]) -> str:
    raw = json.dumps(
        request,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return sha256_bytes(raw)


def validate_ggen_ecosystem_ocel_contract(request: dict[str, Any]) -> None:
    """Independently verify the Project-memory projection emitted by the GGEN pack.

    This does not manufacture OCEL or perform process analysis. It only refuses a
    request that claims the GGEN Ecosystem OCEL contract while diverging from its
    canonical memory identity or required provenance metadata.
    """
    if request.get("operation") != "memory.upsert":
        return
    payload = request.get("payload")
    if not isinstance(payload, dict):
        return
    record = payload.get("record")
    if not isinstance(record, dict):
        return

    tags_raw = record.get("tags")
    tags = {str(tag) for tag in tags_raw} if isinstance(tags_raw, list) else set()
    claims_contract = (
        record.get("key") == GGEN_ECOSYSTEM_OCEL_KEY
        or record.get("kind") == GGEN_ECOSYSTEM_OCEL_KIND
        or {"ggen", "ocel", "manufacturing"}.issubset(tags)
    )
    if not claims_contract:
        return

    metadata = record.get("metadata")
    metadata = metadata if isinstance(metadata, dict) else {}
    failures: list[str] = []
    if record.get("key") != GGEN_ECOSYSTEM_OCEL_KEY:
        failures.append("CANONICAL_KEY_MISMATCH")
    if record.get("kind") != GGEN_ECOSYSTEM_OCEL_KIND:
        failures.append("KIND_MISMATCH")
    if not GGEN_ECOSYSTEM_OCEL_TAGS.issubset(tags):
        failures.append("REQUIRED_TAGS_MISSING")
    if not isinstance(record.get("cell"), str) or not record.get("cell"):
        failures.append("CELL_MISSING")
    if not isinstance(record.get("standing"), str) or not record.get("standing"):
        failures.append("STANDING_MISSING")
    if not isinstance(metadata.get("run_id"), str) or not metadata.get("run_id"):
        failures.append("RUN_ID_MISSING")
    digest = metadata.get("ocel_digest")
    if not isinstance(digest, str) or not digest.startswith("sha256:"):
        failures.append("OCEL_DIGEST_MISSING")
    if metadata.get("manufacturing_ladder") != "U->G->O->Q->M":
        failures.append("MANUFACTURING_LADDER_MISMATCH")
    if metadata.get("ggen_first") is not True:
        failures.append("GGEN_FIRST_REQUIRED")
    if metadata.get("process_analysis_owner") != "wasm4pm":
        failures.append("PROCESS_ANALYSIS_OWNER_MISMATCH")

    if failures:
        raise ValueError(
            json.dumps(
                {
                    "reason": "INVALID_GGEN_ECOSYSTEM_OCEL_CONTRACT",
                    "message": "GGEN Ecosystem OCEL Project-memory projection failed independent admission",
                    "failures": failures,
                },
                sort_keys=True,
            )
        )


def load_request(path: Path) -> tuple[dict[str, Any], str, str]:
    raw = path.read_bytes()
    transport_digest = sha256_bytes(raw)
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(
            json.dumps(
                {
                    "reason": "INVALID_REQUEST_ENCODING",
                    "message": "request must be UTF-8",
                    "start": exc.start,
                    "end": exc.end,
                },
                sort_keys=True,
            )
        ) from exc

    try:
        request = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(
            json.dumps(
                {
                    "reason": "INVALID_REQUEST_JSON",
                    "message": exc.msg,
                    "line": exc.lineno,
                    "column": exc.colno,
                    "offset": exc.pos,
                },
                sort_keys=True,
            )
        ) from exc

    if not isinstance(request, dict):
        raise ValueError(
            json.dumps(
                {
                    "reason": "INVALID_REQUEST_ROOT",
                    "message": "request root must be a JSON object",
                },
                sort_keys=True,
            )
        )

    return request, transport_digest, canonical_digest(request)


def read_receipt(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def is_exact_alive_replay(
    receipt: dict[str, Any] | None,
    *,
    request_sha256: str,
    request_id: str,
    operation: str,
) -> bool:
    if not receipt:
        return False
    return (
        receipt.get("standing") == "ALIVE"
        and receipt.get("request_sha256") == request_sha256
        and receipt.get("request_id") == request_id
        and receipt.get("operation") == operation
    )


def write_transport_refusal(
    *,
    proxy,
    request_path: Path,
    receipt_path: Path,
    transport_digest: str,
    reason: str,
    details: dict[str, Any],
) -> None:
    receipt = {
        "schema": "chatgpt-project-memory-receipt/v1",
        "gate_schema": GATE_SCHEMA,
        "request_path": str(request_path),
        "request_id": None,
        "operation": None,
        "observed_at": proxy.utc_now(),
        "token_source": os.environ.get("PROJECTS_TOKEN_SOURCE", "not-read"),
        "standing": "REFUSED",
        "reason": reason,
        "result": None,
        "error": {
            "type": "TransportAdmissionError",
            "message": details.get("message", reason),
            "details": details,
        },
        "request_digest_basis": {},
        "request_sha256": None,
        "request_transport_sha256": transport_digest,
        "actuation_performed": False,
    }
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(
        json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def augment_receipt(
    receipt_path: Path,
    *,
    request_sha256: str,
    transport_sha256: str,
) -> None:
    receipt = read_receipt(receipt_path)
    if not receipt:
        return
    receipt["gate_schema"] = GATE_SCHEMA
    receipt["request_sha256"] = request_sha256
    receipt["request_transport_sha256"] = transport_sha256
    receipt.setdefault("actuation_performed", receipt.get("standing") == "ALIVE")
    receipt_path.write_text(
        json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _details_from_value_error(exc: ValueError) -> dict[str, Any]:
    try:
        return json.loads(str(exc))
    except json.JSONDecodeError:
        return {"reason": "INVALID_REQUEST", "message": str(exc)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    args = parser.parse_args(argv)

    proxy = load_proxy()
    raw = args.request.read_bytes()
    transport_digest = sha256_bytes(raw)

    try:
        request, transport_digest, request_sha256 = load_request(args.request)
    except ValueError as exc:
        details = _details_from_value_error(exc)
        reason = str(details.get("reason") or "INVALID_REQUEST")
        write_transport_refusal(
            proxy=proxy,
            request_path=args.request,
            receipt_path=args.receipt,
            transport_digest=transport_digest,
            reason=reason,
            details=details,
        )
        print(json.dumps({"standing": "REFUSED", "reason": reason}, sort_keys=True))
        return 2

    try:
        validate_ggen_ecosystem_ocel_contract(request)
    except ValueError as exc:
        details = _details_from_value_error(exc)
        reason = str(details.get("reason") or "INVALID_GGEN_ECOSYSTEM_OCEL_CONTRACT")
        write_transport_refusal(
            proxy=proxy,
            request_path=args.request,
            receipt_path=args.receipt,
            transport_digest=transport_digest,
            reason=reason,
            details=details,
        )
        print(json.dumps({"standing": "REFUSED", "reason": reason}, sort_keys=True))
        return 2

    allowed_owner = os.environ.get("PROJECT_MEMORY_OWNER", "seanchatmangpt")
    allowed_number = int(os.environ.get("PROJECT_MEMORY_NUMBER", "2"))
    try:
        request_id, operation = proxy.validate_request(request, allowed_owner, allowed_number)
    except proxy.ProxyError:
        code = proxy.main(["--request", str(args.request), "--receipt", str(args.receipt)])
        augment_receipt(
            args.receipt,
            request_sha256=request_sha256,
            transport_sha256=transport_digest,
        )
        return code

    existing = read_receipt(args.receipt)
    if is_exact_alive_replay(
        existing,
        request_sha256=request_sha256,
        request_id=request_id,
        operation=operation,
    ):
        print(
            json.dumps(
                {
                    "request_id": request_id,
                    "operation": operation,
                    "standing": "ALIVE",
                    "reason": "IDEMPOTENT_REPLAY",
                    "actuation_performed": False,
                },
                sort_keys=True,
            )
        )
        return 0

    code = proxy.main(["--request", str(args.request), "--receipt", str(args.receipt)])
    augment_receipt(
        args.receipt,
        request_sha256=request_sha256,
        transport_sha256=transport_digest,
    )
    return code


if __name__ == "__main__":
    raise SystemExit(main())
