#!/usr/bin/env python3
"""Canonical client for the bounded local-control transport.

Files typed JSON requests onto a requests directory and fetches typed receipts
from a receipts directory. Envelope bytes are canonical JSON (sorted keys,
compact separators, trailing newline) and are validated against
``local-control/request.schema.json`` before filing; the envelope's
``request_id`` field always equals the written file's stem (the agent refuses
anything else with REQUEST_ID_PATH_MISMATCH).

Subcommands:
  file   --requests-dir DIR --operation OP [--machine ID] [--machine-star]
           [--expires-minutes N] [--payload-json JSON] [--request-id ID]
  list   --requests-dir DIR [--receipts-dir DIR]
  fetch  --request-id ID --receipts-dir DIR [--wait-seconds N] [--poll-seconds S]

``request_id`` defaults to ``<OP>.<yyyymmddTHHMMSSZ>.<4 hex>``. The operation
string must be filename-safe: it may only contain ``[A-Za-z0-9._-]``, must
start with an alphanumeric, must not contain ``..`` or end with ``.``.

Exit codes (typed contract):
  0  success / receipt standing ALIVE
  2  client-side refusal (typed error JSON on stderr, e.g.
     UNSAFE_OPERATION_NAME, UNSAFE_REQUEST_ID, INVALID_PAYLOAD_JSON,
     INVALID_PAYLOAD_JSON, CONFLICTING_MACHINE_OPTIONS,
     INVALID_EXPIRES_MINUTES, SCHEMA_VIOLATION, REQUEST_FILE_EXISTS)
  3  receipt standing REFUSED
  4  receipt standing BUILD_BROKEN
  5  receipt did not appear within --wait-seconds (RECEIPT_TIMEOUT)
  6  unusable receipt (unparseable JSON or standing outside the taxonomy)

Stdlib only; compatible with Python 3.9 and 3.12.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
import secrets
import sys
import time
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCHEMA_PATH = REPO_ROOT / "local-control" / "request.schema.json"

REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,200}$")
OPERATION_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
# request_id = <op> + "." + <16-char UTC stamp> + "." + <4 hex> -> op <= 178
MAX_OPERATION_LENGTH = 178
TIMESTAMP_FORMAT = "%Y%m%dT%H%M%SZ"

STANDING_EXITS = {"ALIVE": 0, "REFUSED": 3, "BUILD_BROKEN": 4}
EXIT_CLIENT_REFUSAL = 2
EXIT_TIMEOUT = 5
EXIT_UNUSABLE_RECEIPT = 6


class ClientRefused(RuntimeError):
    def __init__(self, reason: str, detail: str, exit_code: int = EXIT_CLIENT_REFUSAL):
        super().__init__(detail)
        self.reason = reason
        self.detail = detail
        self.exit_code = exit_code


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def canonical_bytes(value: Any) -> bytes:
    return (canonical_json(value) + "\n").encode("utf-8")


def require_safe_operation(operation: str) -> None:
    if (
        not operation
        or len(operation) > MAX_OPERATION_LENGTH
        or not OPERATION_PATTERN.fullmatch(operation)
        or ".." in operation
        or operation.endswith(".")
    ):
        raise ClientRefused(
            "UNSAFE_OPERATION_NAME",
            f"operation {operation!r} is not filename-safe "
            f"(allowed: [A-Za-z0-9._-], no '..', no trailing '.', max {MAX_OPERATION_LENGTH})",
        )


def require_safe_request_id(request_id: str) -> None:
    if not request_id or not REQUEST_ID_PATTERN.fullmatch(request_id):
        raise ClientRefused(
            "UNSAFE_REQUEST_ID",
            f"request_id {request_id!r} must match {REQUEST_ID_PATTERN.pattern}",
        )


def utc_stamp() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime(TIMESTAMP_FORMAT)


def generate_request_id(operation: str) -> str:
    """request_id = <OP>.<yyyymmddTHHMMSSZ>.<4 hex rand>."""
    return f"{operation}.{utc_stamp()}.{secrets.token_hex(2)}"


def compute_expires_at(minutes: Optional[int]) -> Optional[str]:
    if minutes is None:
        return None
    if minutes < 1:
        raise ClientRefused("INVALID_EXPIRES_MINUTES", f"--expires-minutes must be >= 1, got {minutes}")
    expires = dt.datetime.now(dt.timezone.utc).replace(microsecond=0) + dt.timedelta(minutes=minutes)
    return expires.isoformat()


def parse_payload(raw: Optional[str]) -> Dict[str, Any]:
    if raw is None:
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ClientRefused("INVALID_PAYLOAD_JSON", f"--payload-json is not valid JSON: {exc}")
    if not isinstance(payload, dict):
        raise ClientRefused("INVALID_PAYLOAD_JSON", f"--payload-json must be a JSON object, got {type(payload).__name__}")
    return payload


def resolve_machine(machine: Optional[str], machine_star: bool) -> str:
    if machine and machine_star:
        raise ClientRefused("CONFLICTING_MACHINE_OPTIONS", "--machine and --machine-star are mutually exclusive")
    if machine_star:
        return "*"
    if machine:
        return machine
    return "*"


def build_envelope(
    request_id: str,
    operation: str,
    machine_id: str,
    payload: Dict[str, Any],
    expires_at: Optional[str] = None,
) -> Dict[str, Any]:
    if not machine_id:
        raise ClientRefused("INVALID_MACHINE_ID", "machine id must be a non-empty string")
    envelope: Dict[str, Any] = {
        "request_id": request_id,
        "operation": operation,
        "machine": {"id": machine_id},
        "payload": payload,
    }
    if expires_at:
        envelope["expires_at"] = expires_at
    return envelope


def _type_ok(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "string":
        return isinstance(value, str)
    if expected == "array":
        return isinstance(value, list)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "null":
        return value is None
    return True


def validate_against_schema(value: Any, schema: Dict[str, Any], path: str = "$") -> List[str]:
    """Minimal structural validation (no jsonschema dependency).

    Supports the keywords this transport's schemas use: type, const, enum,
    minLength, maxLength, pattern, required, properties,
    additionalProperties:false. Ignores format.
    """
    violations: List[str] = []
    expected = schema.get("type")
    if isinstance(expected, list):
        if not any(_type_ok(value, item) for item in expected):
            return [f"{path}: expected type {expected}"]
    elif expected is not None and not _type_ok(value, expected):
        return [f"{path}: expected type {expected}"]
    if "const" in schema and value != schema["const"]:
        violations.append(f"{path}: expected const {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        violations.append(f"{path}: value {value!r} not in enum {schema['enum']}")
    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            violations.append(f"{path}: shorter than minLength {schema['minLength']}")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            violations.append(f"{path}: longer than maxLength {schema['maxLength']}")
        if "pattern" in schema and not re.search(schema["pattern"], value):
            violations.append(f"{path}: does not match pattern {schema['pattern']}")
    if isinstance(value, dict):
        properties = schema.get("properties", {})
        for required in schema.get("required", []):
            if required not in value:
                violations.append(f"{path}: missing required property {required!r}")
        if schema.get("additionalProperties") is False:
            for key in value:
                if key not in properties:
                    violations.append(f"{path}: additional property {key!r} not allowed")
        for key, sub_schema in properties.items():
            if key in value:
                violations.extend(validate_against_schema(value[key], sub_schema, f"{path}.{key}"))
    return violations


def load_request_schema(schema_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    path = Path(schema_path) if schema_path else DEFAULT_SCHEMA_PATH
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def file_request(
    requests_dir: Path,
    operation: str,
    machine_id: str,
    payload: Dict[str, Any],
    expires_at: Optional[str] = None,
    request_id: Optional[str] = None,
    schema: Optional[Dict[str, Any]] = None,
) -> Path:
    require_safe_operation(operation)
    request_id = request_id or generate_request_id(operation)
    require_safe_request_id(request_id)
    envelope = build_envelope(request_id, operation, machine_id, payload, expires_at)
    if schema is None:
        schema = load_request_schema()
    if schema is not None:
        violations = validate_against_schema(envelope, schema)
        if violations:
            raise ClientRefused("SCHEMA_VIOLATION", "; ".join(violations))
    else:
        print(
            f"[local-control-request] schema not found at {DEFAULT_SCHEMA_PATH}; "
            "filing without schema validation",
            file=sys.stderr,
        )
    directory = Path(os.path.abspath(str(requests_dir)))
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{request_id}.json"
    if path.exists():
        raise ClientRefused("REQUEST_FILE_EXISTS", f"{path} already exists; request ids are single-use")
    path.write_bytes(canonical_bytes(envelope))
    written = json.loads(path.read_text(encoding="utf-8"))
    if written.get("request_id") != path.stem:
        raise ClientRefused(
            "REQUEST_ID_PATH_MISMATCH",
            f"request_id={written.get('request_id')!r}, path stem={path.stem!r}",
        )
    return path


def cmd_file(args: argparse.Namespace) -> int:
    payload = parse_payload(args.payload_json)
    machine_id = resolve_machine(args.machine, args.machine_star)
    expires_at = compute_expires_at(args.expires_minutes)
    path = file_request(
        requests_dir=Path(args.requests_dir),
        operation=args.operation,
        machine_id=machine_id,
        payload=payload,
        expires_at=expires_at,
        request_id=args.request_id,
    )
    print(str(path))
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    requests_dir = Path(args.requests_dir)
    if args.receipts_dir:
        receipts_dir = Path(args.receipts_dir)
    else:
        receipts_dir = requests_dir.resolve().parent / "receipts"
    for path in sorted(requests_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"[local-control-request] skipping unparseable request {path.name}: {exc}", file=sys.stderr)
            continue
        request_id = str(data.get("request_id") or path.stem)
        operation = str(data.get("operation") or "-")
        machine = str((data.get("machine") or {}).get("id") or "-")
        expires_at = str(data.get("expires_at") or "-")
        status = "RECEIPTED" if (receipts_dir / f"{request_id}.receipt.json").exists() else "MISSING"
        print(f"{request_id} {operation} machine={machine} expires_at={expires_at} {status}")
    return 0


def cmd_fetch(args: argparse.Namespace) -> int:
    require_safe_request_id(args.request_id)
    receipt_path = Path(args.receipts_dir) / f"{args.request_id}.receipt.json"
    deadline = time.monotonic() + max(0.0, args.wait_seconds)
    poll_seconds = max(0.05, args.poll_seconds)
    while True:
        if receipt_path.exists():
            text = receipt_path.read_text(encoding="utf-8")
            try:
                receipt = json.loads(text)
            except json.JSONDecodeError as exc:
                raise ClientRefused(
                    "INVALID_RECEIPT_JSON",
                    f"{receipt_path} is not valid JSON: {exc}",
                    exit_code=EXIT_UNUSABLE_RECEIPT,
                )
            print(text.strip())
            standing = receipt.get("standing") if isinstance(receipt, dict) else None
            if standing in STANDING_EXITS:
                return STANDING_EXITS[standing]
            raise ClientRefused(
                "UNKNOWN_RECEIPT_STANDING",
                f"standing {standing!r} is outside {sorted(STANDING_EXITS)}",
                exit_code=EXIT_UNUSABLE_RECEIPT,
            )
        if time.monotonic() >= deadline:
            raise ClientRefused(
                "RECEIPT_TIMEOUT",
                f"no receipt at {receipt_path} within {args.wait_seconds}s",
                exit_code=EXIT_TIMEOUT,
            )
        time.sleep(min(poll_seconds, max(0.0, deadline - time.monotonic())))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="local_control_request.py",
        description="File local-control requests and fetch receipts (canonical envelope client)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_file = sub.add_parser("file", help="write one canonical request envelope to --requests-dir")
    p_file.add_argument("--requests-dir", required=True)
    p_file.add_argument("--operation", required=True)
    p_file.add_argument("--machine", default=None, help="target machine id (default: broadcast)")
    p_file.add_argument("--machine-star", action="store_true", help='target any machine (machine.id="*")')
    p_file.add_argument("--expires-minutes", type=int, default=None, help="UTC expires_at now + N minutes")
    p_file.add_argument("--payload-json", default=None, help="JSON object payload (default {})")
    p_file.add_argument("--request-id", default=None, help="override generated request_id (must be filename-safe)")
    p_file.set_defaults(func=cmd_file)

    p_list = sub.add_parser("list", help="list requests with RECEIPTED/MISSING status")
    p_list.add_argument("--requests-dir", required=True)
    p_list.add_argument("--receipts-dir", default=None, help="default: <requests-dir>/../receipts")
    p_list.set_defaults(func=cmd_list)

    p_fetch = sub.add_parser("fetch", help="poll for one receipt and exit by standing")
    p_fetch.add_argument("--request-id", required=True)
    p_fetch.add_argument("--receipts-dir", required=True)
    p_fetch.add_argument("--wait-seconds", type=float, default=120.0)
    p_fetch.add_argument("--poll-seconds", type=float, default=2.0)
    p_fetch.set_defaults(func=cmd_fetch)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except ClientRefused as exc:
        print(canonical_json({"error": exc.reason, "detail": exc.detail}), file=sys.stderr)
        return exc.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
