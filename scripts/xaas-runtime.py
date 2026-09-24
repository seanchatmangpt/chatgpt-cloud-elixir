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
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
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
    parsed = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))


def resolve_target(env: dict[str, str] | None = None, url: str | None = None) -> Target:
    env = env or os.environ
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
    data = None if body is None else canonical_json(body)
    headers = {"accept": "application/json"}
    if data is not None:
        headers["content-type"] = "application/json"
    if target.authorization:
        headers["authorization"] = target.authorization
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read()
            status = response.status
    except urllib.error.HTTPError as error:
        raw = error.read()
        status = error.code
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        return 0, None, f"network:{error.__class__.__name__}:{error}"
    try:
        payload = json.loads(raw.decode("utf-8")) if raw else None
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        return status, None, f"protocol:invalid_json:{error}"
    return status, payload, None


def classify_http(status: int, transport_error: str | None) -> tuple[str, str | None]:
    if transport_error:
        if transport_error.startswith("network:"):
            return "BLOCKED", "NETWORK"
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
    if standing == "ALIVE" and isinstance(payload, dict):
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
    if row["standing"] == "ALIVE":
        row["standing"] = "PARTIAL_ALIVE"
        row["reason"] = "RUN_SUBMITTED_NOT_VERIFIED"
        row["downstream_standing"] = "UNKNOWN"
    return row


def read_receipts(target: Target, epoch_id: str, timeout: float) -> dict[str, Any]:
    quoted = urllib.parse.quote(epoch_id, safe="")
    url = target.base_url + f"/internal-api/execution/epochs/{quoted}/receipts"
    status, payload, error = request_json("GET", url, target, None, timeout)
    return receipt(
        action="receipts", url=url, request_body=None, status=status,
        payload=payload, transport_error=error, authenticated=bool(target.authorization),
        replay=f"python3 scripts/xaas-runtime.py receipts {epoch_id}",
    )


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
    return p


def main(argv: list[str] | None = None) -> int:
    p = parser()
    args = p.parse_args(argv)
    target = resolve_target(url=args.url)
    if args.command == "probe":
        row = probe(target, args.timeout)
    elif args.command == "mcp":
        params = None
        if args.method == "tools/call":
            if not args.tool:
                p.error("mcp tools/call requires --tool")
            if args.tool == "actuate" and not args.allow_do:
                row = {
                    "schema": SCHEMA,
                    "observed_at": utc_now(),
                    "subject": "xaas-ultracode-runtime-transport",
                    "standing_scope": "transport",
                    "action": "mcp:tools/call:actuate",
                    "endpoint": endpoint_identity(target.mcp_url),
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
    elif args.command == "submit-run":
        row = submit_run(target, args)
    else:
        row = read_receipts(target, args.epoch_id, args.timeout)
    # Receipts never contain the bearer token; target auth is represented only as a boolean.
    print(json.dumps(row, indent=2, sort_keys=True))
    return exit_code(row)


if __name__ == "__main__":
    raise SystemExit(main())
