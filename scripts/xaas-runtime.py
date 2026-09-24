#!/usr/bin/env python3
"""Receipted ChatGPT-cloud client for the XaaS Ultracode execution fabric.

Uses only the Python standard library so it remains usable before any runtime
capsule is activated. It speaks the same Bearer-gated JSON-RPC/HTTP contract as
zcode-cli's native ``gall-work`` client.

No command grants itself authority. The XaaS token and (for lease tools) the
lease token remain the authority-bearing inputs enforced by XaaS.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import http.client
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_MCP_URL = "http://localhost:4000/internal-api/execution/mcp"
EXPECTED_TOOLS = {
    "claim_next",
    "heartbeat",
    "admit_tool",
    "record_provider_event",
    "close_candidate",
    "refuse",
    "actuate",
}
SCHEMA = "chatgpt-cloud.xaas-runtime-receipt/1"
EXPECTED_SERVER_NAME = "xaas-ultracode-lease"
EXPECTED_PROTOCOL = "2025-03-26"
REQUEST_SCHEMA = "chatgpt-cloud.xaas-runtime-request/1"
REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,128}$")


@dataclass(frozen=True)
class Target:
    mcp_url: str
    authorization: str | None

    @property
    def base_url(self) -> str:
        parsed = urllib.parse.urlsplit(self.mcp_url)
        suffix = "/internal-api/execution/mcp"
        path = parsed.path.rstrip("/")
        if not path.endswith(suffix):
            raise ValueError(
                "XAAS_MCP_URL must end in /internal-api/execution/mcp for run/receipt operations"
            )
        prefix = path[: -len(suffix)]
        return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, prefix, "", ""))


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def endpoint_identity(url: str) -> str:
    """Receipt-safe endpoint: the host of XAAS_MCP_URL is secret-derived and receipts
    are committed to git, so only scheme + path are kept; userinfo, host, port,
    query, and fragment never reach a receipt. Equality is checkable via
    endpoint_sha256."""
    parsed = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit((parsed.scheme, "<redacted-host>", parsed.path, "", ""))


def endpoint_digest(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    host = (parsed.hostname or "").lower()
    port = f":{parsed.port}" if parsed.port else ""
    return hashlib.sha256(f"{parsed.scheme}://{host}{port}{parsed.path}".encode()).hexdigest()


class _RefuseRedirect(urllib.request.HTTPRedirectHandler):
    """Never follow redirects: urllib would replay the bearer to the new location."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D401
        return None


_OPENER = urllib.request.build_opener(_RefuseRedirect)


def target_source(url: str | None = None, env: dict[str, str] | None = None) -> str:
    if env is None:
        env = os.environ
    if url:
        return "flag"
    if (env.get("XAAS_MCP_URL") or "").strip():
        return "env"
    return "default"


def resolve_target(env: dict[str, str] | None = None, url: str | None = None) -> Target:
    if env is None:
        env = os.environ
    mcp_url = (url or env.get("XAAS_MCP_URL") or DEFAULT_MCP_URL).strip()
    token = (env.get("XAAS_MCP_TOKEN") or "").strip()
    return Target(mcp_url=mcp_url, authorization=f"Bearer {token}" if token else None)


def request_json(
    method: str,
    url: str,
    target: Target,
    body: Any | None = None,
    timeout: float = 15.0,
) -> tuple[int, Any, str | None]:
    parsed = urllib.parse.urlsplit(url)
    if parsed.username is not None or parsed.password is not None:
        # Credentials belong in XAAS_MCP_TOKEN only; never hand userinfo to urllib/proxies.
        return 0, None, "config:url_userinfo_refused"
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return 0, None, "config:url_invalid"
    data = None if body is None else canonical_json(body)
    headers = {"accept": "application/json"}
    if data is not None:
        headers["content-type"] = "application/json"
    if target.authorization:
        headers["authorization"] = target.authorization
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with _OPENER.open(req, timeout=timeout) as response:
            raw = response.read()
            status = response.status
    except urllib.error.HTTPError as error:
        status = error.code
        if 300 <= status < 400:
            return status, None, "redirect:refused"
        raw = error.read()
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        return 0, None, f"network:{error.__class__.__name__}:{error}"
    except http.client.HTTPException as error:
        return 0, None, f"protocol:http:{error.__class__.__name__}"
    try:
        payload = json.loads(raw.decode("utf-8")) if raw else None
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        return status, None, f"protocol:invalid_json:{error}"
    return status, payload, None


def classify_http(status: int, transport_error: str | None) -> tuple[str, str | None]:
    if transport_error:
        if transport_error.startswith("network:"):
            return "BLOCKED", "NETWORK"
        if transport_error.startswith("config:"):
            return "BLOCKED", "IRREDUCIBLE_TRANSPORT_CONFIG"
        if transport_error.startswith("redirect:"):
            return "BLOCKED", "REDIRECT_REFUSED"
        return "BUILD_BROKEN", "PROTOCOL"
    if 200 <= status < 300:
        return "ALIVE", None
    if status == 401:
        return "REFUSED_AUTHENTICATION", "AUTHENTICATION"
    if status == 403:
        return "REFUSED_AUTHORITY", "AUTHORITY"
    if status == 429:
        return "BLOCKED", "CAPACITY"
    if status == 503:
        return "BLOCKED", "SERVER_MISCONFIGURED"
    if status == 404:
        return "BLOCKED", "NOT_FOUND_OR_NOT_VISIBLE"
    if 400 <= status < 500:
        return "REFUSED_REQUEST", f"HTTP_{status}"
    return "BLOCKED", f"HTTP_{status}"


def receipt(
    *, action: str, url: str, request_body: Any | None, status: int,
    payload: Any, transport_error: str | None, authenticated: bool,
    standing: str | None = None, reason: str | None = None, replay: str,
) -> dict[str, Any]:
    inferred_standing, inferred_reason = classify_http(status, transport_error)
    return {
        "schema": SCHEMA,
        "observed_at": utc_now(),
        "subject": "xaas-ultracode-runtime-transport",
        "standing_scope": "transport",
        "action": action,
        "endpoint": endpoint_identity(url),
        "endpoint_sha256": endpoint_digest(url),
        "authenticated": authenticated,
        "request_sha256": digest(request_body) if request_body is not None else None,
        "http_status": status or None,
        "response": payload,
        "transport_error": transport_error,
        "standing": standing or inferred_standing,
        "reason": reason or inferred_reason,
        "replay": replay,
    }


def mcp_call(target: Target, method: str, params: dict[str, Any] | None, timeout: float) -> dict[str, Any]:
    body: dict[str, Any] = {"jsonrpc": "2.0", "id": 1, "method": method}
    if params is not None:
        body["params"] = params
    status, payload, error = request_json("POST", target.mcp_url, target, body, timeout)
    standing, reason = classify_http(status, error)
    if standing == "ALIVE" and not (isinstance(payload, dict) and ("result" in payload or payload.get("error"))):
        standing, reason = "BUILD_BROKEN", "PROTOCOL_SHAPE"
    elif standing == "ALIVE":
        if payload.get("error"):
            standing, reason = "REFUSED_REQUEST", "JSON_RPC_ERROR"
        result = payload.get("result")
        if isinstance(result, dict) and result.get("isError") is True:
            standing, reason = "REFUSED_REQUEST", "TOOL_REFUSAL"
    return receipt(
        action=f"mcp:{method}", url=target.mcp_url, request_body=body,
        status=status, payload=payload, transport_error=error, authenticated=bool(target.authorization),
        standing=standing, reason=reason,
        replay=f"python3 scripts/xaas-runtime.py mcp {method}",
    )


def probe(target: Target, timeout: float) -> dict[str, Any]:
    init = mcp_call(target, "initialize", None, timeout)
    if init["standing"] != "ALIVE":
        init["action"] = "probe"
        init["replay"] = "python3 scripts/xaas-runtime.py probe"
        return init
    try:
        init_result = init["response"]["result"]
        server_name = init_result["serverInfo"]["name"]
        protocol = init_result["protocolVersion"]
    except (KeyError, TypeError):
        server_name, protocol = None, None
    listed = mcp_call(target, "tools/list", None, timeout)
    if listed["standing"] != "ALIVE":
        listed["action"] = "probe"
        listed["replay"] = "python3 scripts/xaas-runtime.py probe"
        return listed
    try:
        tools = listed["response"]["result"]["tools"]
        names = {tool["name"] for tool in tools}
    except (KeyError, TypeError):
        names = set()
    missing = sorted(EXPECTED_TOOLS - names)
    extra = sorted(names - EXPECTED_TOOLS)
    identity_ok = server_name == EXPECTED_SERVER_NAME and protocol == EXPECTED_PROTOCOL
    listed.update({
        "action": "probe",
        "contract": {
            "expected_server_name": EXPECTED_SERVER_NAME,
            "observed_server_name": server_name,
            "expected_protocol": EXPECTED_PROTOCOL,
            "observed_protocol": protocol,
            "expected_tools": sorted(EXPECTED_TOOLS),
            "observed_tools": sorted(names),
            "missing": missing,
            "extra": extra
        },
        "standing": "ALIVE" if identity_ok and not missing else "UNSUPPORTED",
        "reason": None if identity_ok and not missing else "CONTRACT_MISMATCH",
        "replay": "python3 scripts/xaas-runtime.py probe",
    })
    return listed


def submit_run(target: Target, args: argparse.Namespace) -> dict[str, Any]:
    body = {"goal": args.goal, "provider": args.provider}
    if args.worktree:
        body["worktree"] = args.worktree
    if args.exact_subject:
        body["exact_subject"] = args.exact_subject
    if args.verifier_suite:
        body["verifier_suite"] = args.verifier_suite
    url = target.base_url + "/internal-api/execution/runs"
    status, payload, error = request_json("POST", url, target, body, args.timeout)
    row = receipt(
        action="submit-run", url=url, request_body=body, status=status,
        payload=payload, transport_error=error, authenticated=bool(target.authorization),
        replay="python3 scripts/xaas-runtime.py submit-run --goal <goal> [--worktree <xaas-host-path>]",
    )
    if row["standing"] == "ALIVE" and not isinstance(payload, dict):
        row["standing"], row["reason"] = "BUILD_BROKEN", "PROTOCOL_SHAPE"
    if row["standing"] == "ALIVE":
        row["standing"] = "PARTIAL_ALIVE"
        row["reason"] = "RUN_SUBMITTED_NOT_VERIFIED"
        row["downstream_standing"] = "UNKNOWN"
    return row


def read_receipts(target: Target, epoch_id: str, timeout: float) -> dict[str, Any]:
    quoted = urllib.parse.quote(epoch_id, safe="")
    url = target.base_url + f"/internal-api/execution/epochs/{quoted}/receipts"
    status, payload, error = request_json("GET", url, target, None, timeout)
    row = receipt(
        action="receipts", url=url, request_body=None, status=status,
        payload=payload, transport_error=error, authenticated=bool(target.authorization),
        replay=f"python3 scripts/xaas-runtime.py receipts {epoch_id}",
    )
    if row["standing"] == "ALIVE" and not isinstance(payload, dict):
        row["standing"], row["reason"] = "BUILD_BROKEN", "PROTOCOL_SHAPE"
    return row



def local_request_receipt(
    request_id: str,
    operation: str,
    standing: str,
    reason: str,
    detail: str | None = None,
) -> dict[str, Any]:
    row = {
        "schema": SCHEMA,
        "observed_at": utc_now(),
        "subject": "xaas-ultracode-runtime-transport",
        "standing_scope": "transport",
        "action": operation,
        "endpoint": None,
        "authenticated": False,
        "request_sha256": None,
        "http_status": None,
        "response": None,
        "transport_error": None,
        "standing": standing,
        "reason": reason,
        "replay": "python3 scripts/xaas-runtime.py request --request <request.json> --receipt <receipt.json> --require-config",
        "request_id": request_id,
        "operation": operation,
    }
    if detail:
        row["detail"] = detail
    return row


def missing_config(url: str | None = None, env: dict[str, str] | None = None) -> list[str]:
    if env is None:
        env = os.environ
    missing = []
    if not (url or env.get("XAAS_MCP_URL", "")).strip():
        missing.append("XAAS_MCP_URL")
    if not env.get("XAAS_MCP_TOKEN", "").strip():
        missing.append("XAAS_MCP_TOKEN")
    return missing


def execute_request_document(
    document: dict[str, Any],
    target: Target | None,
    timeout: float,
    require_config: bool = False,
) -> dict[str, Any]:
    request_id = str(document.get("request_id") or "")
    operation = str(document.get("operation") or "")

    def bound(row: dict[str, Any]) -> dict[str, Any]:
        row["request_id"] = request_id or "invalid"
        row["operation"] = operation or "invalid"
        row["request_document_sha256"] = digest(document)
        return row

    if document.get("schema") != REQUEST_SCHEMA:
        return bound(local_request_receipt(request_id or "invalid", operation or "invalid", "REFUSED_REQUEST", "REQUEST_SCHEMA_MISMATCH"))
    if not REQUEST_ID.fullmatch(request_id):
        return bound(local_request_receipt(request_id or "invalid", operation or "invalid", "REFUSED_REQUEST", "REQUEST_ID_INVALID"))
    payload = document.get("payload", {})
    if not isinstance(payload, dict):
        return bound(local_request_receipt(request_id, operation, "REFUSED_REQUEST", "PAYLOAD_NOT_OBJECT"))

    if require_config:
        missing = missing_config()
        if missing:
            return bound(local_request_receipt(
                request_id,
                operation,
                "BLOCKED",
                "IRREDUCIBLE_TRANSPORT_CONFIG",
                "missing environment: " + ",".join(missing),
            ))
    if target is None:
        target = resolve_target()

    if operation == "fabric.probe":
        row = probe(target, timeout)
    elif operation == "run.submit":
        goal = payload.get("goal")
        exact_subject = payload.get("exact_subject")
        provider = payload.get("provider", "zcode")
        if not isinstance(goal, str) or not goal.strip():
            return bound(local_request_receipt(request_id, operation, "REFUSED_REQUEST", "GOAL_REQUIRED"))
        if not isinstance(exact_subject, str) or not exact_subject.strip():
            return bound(local_request_receipt(request_id, operation, "REFUSED_REQUEST", "EXACT_SUBJECT_REQUIRED"))
        if provider != "zcode":
            return bound(local_request_receipt(request_id, operation, "REFUSED_REQUEST", "PROVIDER_UNSUPPORTED"))
        args = argparse.Namespace(
            goal=goal,
            provider="zcode",
            worktree=payload.get("worktree"),
            exact_subject=exact_subject,
            verifier_suite=payload.get("verifier_suite"),
            timeout=timeout,
        )
        row = submit_run(target, args)
    elif operation == "epoch.receipts":
        epoch_id = payload.get("epoch_id")
        try:
            normalized = str(uuid.UUID(str(epoch_id)))
        except (ValueError, TypeError, AttributeError):
            return bound(local_request_receipt(request_id, operation, "REFUSED_REQUEST", "EPOCH_ID_INVALID"))
        row = read_receipts(target, normalized, timeout)
    else:
        return bound(local_request_receipt(request_id, operation or "invalid", "REFUSED_REQUEST", "OPERATION_UNSUPPORTED"))

    return bound(row)


def run_request_file(args: argparse.Namespace) -> dict[str, Any]:
    request_path = args.request.resolve()
    try:
        document = json.loads(request_path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        row = local_request_receipt(
            request_path.stem or "invalid",
            "invalid",
            "BUILD_BROKEN",
            "REQUEST_UNREADABLE",
            str(error),
        )
    else:
        if not isinstance(document, dict):
            row = local_request_receipt(
                request_path.stem or "invalid",
                "invalid",
                "REFUSED_REQUEST",
                "REQUEST_NOT_OBJECT",
            )
            row["request_document_sha256"] = digest(document)
        else:
            request_id = str(document.get("request_id") or "")
            if request_id and request_path.stem != request_id:
                row = local_request_receipt(
                    request_id,
                    str(document.get("operation") or "invalid"),
                    "REFUSED_REQUEST",
                    "REQUEST_FILENAME_MISMATCH",
                )
                row["request_document_sha256"] = digest(document)
            else:
                try:
                    row = execute_request_document(document, None, args.timeout, args.require_config)
                except ValueError as error:
                    row = local_request_receipt(
                        request_id or "invalid",
                        str(document.get("operation") or "invalid"),
                        "BLOCKED",
                        "IRREDUCIBLE_TRANSPORT_CONFIG",
                        str(error),
                    )
                    row["request_document_sha256"] = digest(document)
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(row, indent=2, sort_keys=True) + "\n")
    return row


def parse_json_object(text: str) -> dict[str, Any]:
    value = json.loads(text)
    if not isinstance(value, dict):
        raise argparse.ArgumentTypeError("arguments must decode to a JSON object")
    return value


def exit_code(row: dict[str, Any]) -> int:
    standing = row["standing"]
    if standing in {"ALIVE", "PARTIAL_ALIVE"}:
        return 0
    if standing.startswith("REFUSED"):
        return 77
    if standing == "UNSUPPORTED":
        return 64
    if standing == "BUILD_BROKEN":
        return 65
    return 69


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--url", help="override XAAS_MCP_URL")
    p.add_argument("--timeout", type=float, default=15.0)
    p.add_argument(
        "--require-config",
        dest="require_config_global",
        action="store_true",
        help="refuse to fall back to the localhost default; missing XAAS_MCP_URL/XAAS_MCP_TOKEN is BLOCKED[IRREDUCIBLE_TRANSPORT_CONFIG]",
    )
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("probe", help="initialize and verify the seven-tool Ultracode MCP contract")
    mcp = sub.add_parser("mcp", help="call an MCP method or fabric tool")
    mcp.add_argument("method", help="initialize, tools/list, or tools/call")
    mcp.add_argument("--tool", help="tool name when method=tools/call")
    mcp.add_argument("--arguments", type=parse_json_object, default={})
    mcp.add_argument("--allow-do", action="store_true", help="required for the Ultracode actuate DO verb")
    submit = sub.add_parser("submit-run", help="submit a zcode-claimable Ultracode Run")
    submit.add_argument("--goal", required=True)
    submit.add_argument("--provider", default="zcode")
    submit.add_argument("--worktree", help="absolute path on the XaaS host; omit if server workflow materializes it")
    submit.add_argument("--exact-subject")
    submit.add_argument("--verifier-suite")
    receipts = sub.add_parser("receipts", help="read sealed receipts for one epoch")
    receipts.add_argument("epoch_id")
    request = sub.add_parser("request", help="execute one bounded GitHub-relay request document")
    request.add_argument("--request", type=Path, required=True)
    request.add_argument("--receipt", type=Path, required=True)
    request.add_argument("--require-config", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    p = parser()
    args = p.parse_args(argv)
    target = resolve_target(url=args.url)
    if args.require_config_global and args.command != "request":
        # Direct (non-relay) path: an absent target is a configuration edge, not a
        # network edge. Never let the localhost default masquerade as NETWORK.
        missing = missing_config(args.url)
        if missing:
            row = local_request_receipt(
                "direct",
                args.command,
                "BLOCKED",
                "IRREDUCIBLE_TRANSPORT_CONFIG",
                "missing environment: " + ",".join(missing),
            )
            row.pop("request_id")
            row.pop("operation")
            row["target_source"] = target_source(args.url)
            row["replay"] = f"python3 scripts/xaas-runtime.py --require-config {args.command}"
            print(json.dumps(row, indent=2, sort_keys=True))
            return exit_code(row)
    if args.command == "probe":
        row = probe(target, args.timeout)
    elif args.command == "mcp":
        params = None
        if args.method == "tools/call":
            if not args.tool:
                p.error("mcp tools/call requires --tool")
            if args.tool.strip().casefold() == "actuate" and not args.allow_do:
                row = {
                    "schema": SCHEMA,
                    "observed_at": utc_now(),
                    "subject": "xaas-ultracode-runtime-transport",
                    "standing_scope": "transport",
                    "action": "mcp:tools/call:actuate",
                    "endpoint": endpoint_identity(target.mcp_url),
                    "endpoint_sha256": endpoint_digest(target.mcp_url),
                    "authenticated": bool(target.authorization),
                    "request_sha256": digest(args.arguments),
                    "http_status": None,
                    "response": None,
                    "transport_error": None,
                    "standing": "REFUSED_AUTHORITY",
                    "reason": "EXPLICIT_DO_ACK_REQUIRED",
                    "replay": "python3 scripts/xaas-runtime.py mcp tools/call --tool actuate --allow-do --arguments <json>",
                }
                print(json.dumps(row, indent=2, sort_keys=True))
                return exit_code(row)
            params = {"name": args.tool, "arguments": args.arguments}
        row = mcp_call(target, args.method, params, args.timeout)
    elif args.command in {"submit-run", "receipts"}:
        try:
            _ = target.base_url
        except ValueError as error:
            row = local_request_receipt("direct", args.command, "BLOCKED", "IRREDUCIBLE_TRANSPORT_CONFIG", str(error))
            row.pop("request_id")
            row.pop("operation")
        else:
            if args.command == "submit-run":
                row = submit_run(target, args)
            else:
                row = read_receipts(target, args.epoch_id, args.timeout)
    else:
        args.require_config = args.require_config or args.require_config_global
        row = run_request_file(args)
    # Receipts never contain the bearer token; target auth is represented only as a boolean.
    if args.command != "request":
        row.setdefault("target_source", target_source(args.url))
    print(json.dumps(row, indent=2, sort_keys=True))
    return exit_code(row)


if __name__ == "__main__":
    raise SystemExit(main())
