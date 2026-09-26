#!/usr/bin/env python3
"""Receipted ChatGPT-cloud client for the XaaS Ultracode execution fabric.

Uses only the Python standard library so it remains usable before any runtime
capsule is activated. It speaks the same Bearer-gated JSON-RPC/HTTP contract as
zcode-cli's native ``gall-work`` client.

Transports (--transport):

- ``http`` (default): direct Bearer-gated HTTP against XAAS_MCP_URL.
- ``wss`` (target architecture, v26.9.25): direct WebSocket (RFC 6455, ws:// or
  wss://) dial of the XaaS outbound tunnel at XAAS_TUNNEL_URL, token
  XAAS_TUNNEL_TOKEN. Carries only the bounded trio fabric.probe / run.submit /
  epoch.receipts; the probe -> admit -> submit -> execute -> sealedReceipt ->
  replay sequence is unchanged, only the wire changes.
- ``github-actions``: explicit fallback transport (request/receipt relay via
  .github/workflows/xaas-runtime-proxy.yml). Selected only when wss fails with
  a typed transport reason (R25-015: transport failure is typed, never subject
  failure).

No command grants itself authority. The XaaS token and (for lease tools) the
lease token remain the authority-bearing inputs enforced by XaaS.
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import http.client
import json
import os
import re
import socket
import ssl
import struct
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_MCP_URL = "http://localhost:4000/internal-api/execution/mcp"
MCP_PATH = "/internal-api/execution/mcp"
RUNS_PATH = "/internal-api/execution/runs"
TRIO_OPERATIONS = {"fabric.probe", "run.submit", "epoch.receipts"}
MAX_WS_FRAME = 4 * 1024 * 1024
WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
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


@dataclass(frozen=True)
class TunnelTarget:
    url: str
    token: str | None


def resolve_tunnel(env: dict[str, str] | None = None, url: str | None = None) -> TunnelTarget:
    if env is None:
        env = os.environ
    tunnel_url = (url or env.get("XAAS_TUNNEL_URL") or "").strip()
    token = (env.get("XAAS_TUNNEL_TOKEN") or "").strip()
    return TunnelTarget(url=tunnel_url, token=token or None)


def missing_tunnel_config(url: str | None = None, env: dict[str, str] | None = None) -> list[str]:
    if env is None:
        env = os.environ
    missing = []
    if not (url or env.get("XAAS_TUNNEL_URL", "")).strip():
        missing.append("XAAS_TUNNEL_URL")
    if not env.get("XAAS_TUNNEL_TOKEN", "").strip():
        missing.append("XAAS_TUNNEL_TOKEN")
    return missing


def tunnel_config_error(tunnel: TunnelTarget) -> str | None:
    """Shape validation before any dial; same privacy law as the HTTP surface."""
    parsed = urllib.parse.urlsplit(tunnel.url)
    if parsed.username is not None or parsed.password is not None:
        return "config:url_userinfo_refused"
    if parsed.scheme not in {"ws", "wss"} or not parsed.hostname:
        return "config:url_invalid"
    return None


def tunnel_origin(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))


class TransportError(Exception):
    """Typed machine-readable transport failure; never a subject verdict."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _ws_connect_tcp(host: str, port: int, timeout: float, tls: bool, server_hostname: str) -> socket.socket:
    raw = socket.create_connection((host, port), timeout=timeout)
    if tls:
        context = ssl.create_default_context()
        return context.wrap_socket(raw, server_hostname=server_hostname)
    return raw


def _ws_read_handshake_response(sock: socket.socket) -> tuple[int, dict[str, str]]:
    data = b""
    while b"\r\n\r\n" not in data:
        chunk = sock.recv(4096)
        if not chunk:
            raise TransportError("transport:handshake_eof")
        data += chunk
        if len(data) > 65536:
            raise TransportError("protocol:ws:handshake_too_large")
    head = data.split(b"\r\n\r\n", 1)[0].decode("latin-1")
    lines = head.split("\r\n")
    try:
        status = int(lines[0].split(" ")[1])
    except (IndexError, ValueError):
        raise TransportError("protocol:ws:handshake_shape")
    headers: dict[str, str] = {}
    for line in lines[1:]:
        if ":" in line:
            key, value = line.split(":", 1)
            headers[key.strip().lower()] = value.strip()
    return status, headers


def ws_connect(url: str, token: str | None = None, timeout: float = 15.0) -> "WsSocket":
    """Dial a ws:// or wss:// endpoint per RFC 6455 using only the stdlib.

    The bearer token, when present, is sent in the upgrade handshake
    ``Authorization`` header. Failures are TransportError with typed codes;
    nothing here decides subject standing.
    """
    parsed = urllib.parse.urlsplit(url)
    if parsed.username is not None or parsed.password is not None:
        raise TransportError("config:url_userinfo_refused")
    if parsed.scheme not in {"ws", "wss"} or not parsed.hostname:
        raise TransportError("config:url_invalid")
    tls = parsed.scheme == "wss"
    port = parsed.port or (443 if tls else 80)
    path = parsed.path or "/"
    if parsed.query:
        path += "?" + parsed.query
    key = base64.b64encode(os.urandom(16)).decode()
    request_lines = [
        f"GET {path} HTTP/1.1",
        f"host: {parsed.netloc}",
        "upgrade: websocket",
        "connection: Upgrade",
        f"sec-websocket-key: {key}",
        "sec-websocket-version: 13",
    ]
    if token:
        request_lines.append(f"authorization: Bearer {token}")
    request = ("\r\n".join(request_lines) + "\r\n\r\n").encode("latin-1")
    try:
        sock = _ws_connect_tcp(parsed.hostname, port, timeout, tls, parsed.hostname)
        sock.settimeout(timeout)
        sock.sendall(request)
        status, headers = _ws_read_handshake_response(sock)
    except TransportError:
        raise
    except socket.timeout:
        raise TransportError("transport:timeout")
    except (OSError, ssl.SSLError) as error:
        raise TransportError(f"transport:connect:{error.__class__.__name__}")
    if status != 101:
        try:
            sock.close()
        except OSError:
            pass
        if status == 401:
            raise TransportError("refused_auth:handshake_401")
        if status == 403:
            raise TransportError("refused_authz:handshake_403")
        raise TransportError(f"transport:handshake_{status}")
    expected = base64.b64encode(hashlib.sha256((key + WS_GUID).encode()).digest()).decode()
    if headers.get("sec-websocket-accept") != expected:
        try:
            sock.close()
        except OSError:
            pass
        raise TransportError("protocol:ws:accept_mismatch")
    return WsSocket(sock)


def _ws_send_frame(sock: socket.socket, opcode: int, payload: bytes, timeout: float) -> None:
    sock.settimeout(timeout)
    header = bytearray([0x80 | opcode])
    mask_bit = 0x80  # client-to-server frames are always masked (RFC 6455 5.3)
    length = len(payload)
    if length < 126:
        header.append(mask_bit | length)
    elif length < 65536:
        header.append(mask_bit | 126)
        header += struct.pack(">H", length)
    else:
        header.append(mask_bit | 127)
        header += struct.pack(">Q", length)
    mask = os.urandom(4)
    header += mask
    masked = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
    sock.sendall(bytes(header) + masked)


def _ws_recv_exact(sock: socket.socket, count: int) -> bytes:
    chunks = bytearray()
    while len(chunks) < count:
        chunk = sock.recv(count - len(chunks))
        if not chunk:
            raise TransportError("transport:ws_eof")
        chunks += chunk
    return bytes(chunks)


def _ws_recv_frame(sock: socket.socket, timeout: float) -> tuple[bool, int, bytes]:
    sock.settimeout(timeout)
    first, second = _ws_recv_exact(sock, 2)
    fin = bool(first & 0x80)
    opcode = first & 0x0F
    masked = bool(second & 0x80)
    length = second & 0x7F
    if length == 126:
        length = struct.unpack(">H", _ws_recv_exact(sock, 2))[0]
    elif length == 127:
        length = struct.unpack(">Q", _ws_recv_exact(sock, 8))[0]
    if length > MAX_WS_FRAME:
        raise TransportError("protocol:ws:frame_too_large")
    mask = _ws_recv_exact(sock, 4) if masked else None
    payload = _ws_recv_exact(sock, length) if length else b""
    if mask:
        payload = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
    return fin, opcode, payload


class WsSocket:
    """Minimal text-frame WebSocket with ping/close handling and a hard frame cap."""

    def __init__(self, sock: socket.socket):
        self._sock = sock

    def send_text(self, text: str, timeout: float = 15.0) -> None:
        _ws_send_frame(self._sock, 0x1, text.encode("utf-8"), timeout)

    def recv_text(self, timeout: float = 15.0) -> str:
        buffer = b""
        started = False
        while True:
            fin, opcode, payload = _ws_recv_frame(self._sock, timeout)
            if opcode == 0x9:  # ping -> pong
                _ws_send_frame(self._sock, 0xA, payload, timeout)
                continue
            if opcode == 0xA:  # unsolicited pong
                continue
            if opcode == 0x8:  # close
                raise TransportError("transport:ws_closed")
            if opcode in (0x1, 0x2):
                if started:
                    raise TransportError("protocol:ws:unterminated_message")
                buffer, started = payload, True
            elif opcode == 0x0:
                if not started:
                    raise TransportError("protocol:ws:stray_continuation")
                buffer += payload
            else:
                raise TransportError(f"protocol:ws:opcode_{opcode}")
            if fin:
                return buffer.decode("utf-8")

    def close(self) -> None:
        try:
            _ws_send_frame(self._sock, 0x8, b"", 2.0)
        except OSError:
            pass
        try:
            self._sock.close()
        except OSError:
            pass


def tunnel_exchange(
    tunnel: TunnelTarget,
    method: str,
    path: str,
    body: Any | None,
    timeout: float,
) -> tuple[int, Any, str | None]:
    """One request/response over the XaaS tunnel: dial, send envelope frame,
    await one response frame, close. Same (status, payload, transport_error)
    triple as request_json so the operation layer is transport-agnostic.

    Envelope contract (implemented by Xaas.Tunnel on the xaas side):
      -> {"v":1,"kind":"http","method":...,"path":...,"headers":{...},"body":...}
      <- {"v":1,"kind":"http_response","status":...,"body":...}
    """
    try:
        ws = ws_connect(tunnel.url, tunnel.token, timeout)
    except TransportError as error:
        return 0, None, error.code
    envelope: dict[str, Any] = {
        "v": 1,
        "kind": "http",
        "method": method,
        "path": path,
        "headers": {},
        "body": body,
    }
    if tunnel.token:
        envelope["headers"] = {"authorization": f"Bearer {tunnel.token}"}
    try:
        ws.send_text(canonical_json(envelope).decode("utf-8"), timeout)
        raw = ws.recv_text(timeout)
    except TransportError as error:
        return 0, None, error.code
    except socket.timeout:
        return 0, None, "transport:timeout"
    except (OSError, UnicodeDecodeError) as error:
        return 0, None, f"transport:{error.__class__.__name__}"
    finally:
        ws.close()
    try:
        response = json.loads(raw)
    except json.JSONDecodeError as error:
        return 0, None, f"protocol:ws:invalid_json:{error}"
    if not isinstance(response, dict) or not isinstance(response.get("status"), int):
        return 0, None, "protocol:ws:tunnel_shape"
    return int(response["status"]), response.get("body"), None


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
        if transport_error.startswith("transport:"):
            # R25-015: a transport failure is typed as transport, never as subject failure.
            return "BLOCKED", "TRANSPORT"
        if transport_error.startswith("refused_auth:"):
            return "REFUSED_AUTHENTICATION", "AUTHENTICATION"
        if transport_error.startswith("refused_authz:"):
            return "REFUSED_AUTHORITY", "AUTHORITY"
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


def http_exchange(target: Target):
    """Exchange closure over the direct HTTP surface.

    exchange(method, path, body, timeout) -> (url, status, payload, transport_error)
    """

    def exchange(method: str, path: str, body: Any | None, timeout: float):
        url = target.mcp_url if path == MCP_PATH else target.base_url + path
        status, payload, error = request_json(method, url, target, body, timeout)
        return url, status, payload, error

    return exchange


def wss_exchange(tunnel: TunnelTarget):
    """Exchange closure over the direct WSS tunnel. Receipt urls keep the ws/wss
    scheme plus the API path; the host is redacted by endpoint_identity."""

    origin = tunnel_origin(tunnel.url)

    def exchange(method: str, path: str, body: Any | None, timeout: float):
        status, payload, error = tunnel_exchange(tunnel, method, path, body, timeout)
        return origin + path, status, payload, error

    return exchange


def mcp_call_exchange(
    exchange,
    method: str,
    params: dict[str, Any] | None,
    timeout: float,
    authenticated: bool,
) -> dict[str, Any]:
    body: dict[str, Any] = {"jsonrpc": "2.0", "id": 1, "method": method}
    if params is not None:
        body["params"] = params
    url, status, payload, error = exchange("POST", MCP_PATH, body, timeout)
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
        action=f"mcp:{method}", url=url, request_body=body,
        status=status, payload=payload, transport_error=error, authenticated=authenticated,
        standing=standing, reason=reason,
        replay=f"python3 scripts/xaas-runtime.py mcp {method}",
    )


def mcp_call(target: Target, method: str, params: dict[str, Any] | None, timeout: float) -> dict[str, Any]:
    return mcp_call_exchange(http_exchange(target), method, params, timeout, bool(target.authorization))


def probe(target: Target, timeout: float, exchange=None, authenticated: bool | None = None) -> dict[str, Any]:
    if exchange is None:
        exchange = http_exchange(target)
    if authenticated is None:
        authenticated = bool(target.authorization)
    init = mcp_call_exchange(exchange, "initialize", None, timeout, authenticated)
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
    listed = mcp_call_exchange(exchange, "tools/list", None, timeout, authenticated)
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


def submit_run(target: Target, args: argparse.Namespace, exchange=None, authenticated: bool | None = None) -> dict[str, Any]:
    if exchange is None:
        exchange = http_exchange(target)
    if authenticated is None:
        authenticated = bool(target.authorization)
    body = {"goal": args.goal, "provider": args.provider}
    if args.worktree:
        body["worktree"] = args.worktree
    if args.exact_subject:
        body["exact_subject"] = args.exact_subject
    if args.verifier_suite:
        body["verifier_suite"] = args.verifier_suite
    url, status, payload, error = exchange("POST", RUNS_PATH, body, args.timeout)
    row = receipt(
        action="submit-run", url=url, request_body=body, status=status,
        payload=payload, transport_error=error, authenticated=authenticated,
        replay="python3 scripts/xaas-runtime.py submit-run --goal <goal> [--worktree <xaas-host-path>]",
    )
    if row["standing"] == "ALIVE" and not isinstance(payload, dict):
        row["standing"], row["reason"] = "BUILD_BROKEN", "PROTOCOL_SHAPE"
    if row["standing"] == "ALIVE":
        row["standing"] = "PARTIAL_ALIVE"
        row["reason"] = "RUN_SUBMITTED_NOT_VERIFIED"
        row["downstream_standing"] = "UNKNOWN"
    return row


def read_receipts(target: Target, epoch_id: str, timeout: float, exchange=None, authenticated: bool | None = None) -> dict[str, Any]:
    if exchange is None:
        exchange = http_exchange(target)
    if authenticated is None:
        authenticated = bool(target.authorization)
    quoted = urllib.parse.quote(epoch_id, safe="")
    url, status, payload, error = exchange("GET", f"/internal-api/execution/epochs/{quoted}/receipts", None, timeout)
    row = receipt(
        action="receipts", url=url, request_body=None, status=status,
        payload=payload, transport_error=error, authenticated=authenticated,
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


def note_fallback(row: dict[str, Any]) -> dict[str, Any]:
    """R25-015: a typed wss transport failure is the only condition that selects
    the github-actions fallback transport. Recorded on the receipt, never guessed."""
    if row.get("standing") == "BLOCKED" and row.get("reason") == "TRANSPORT":
        row["fallback_transport"] = "github-actions"
        row["fallback_note"] = (
            "wss transport failed with a typed transport reason; the github-actions "
            "request/receipt relay is the explicit fallback, not the target architecture"
        )
    return row


def execute_request_document(
    document: dict[str, Any],
    target: Target | None,
    timeout: float,
    require_config: bool = False,
    transport: str = "http",
    tunnel: TunnelTarget | None = None,
) -> dict[str, Any]:
    request_id = str(document.get("request_id") or "")
    operation = str(document.get("operation") or "")

    def bound(row: dict[str, Any]) -> dict[str, Any]:
        row["request_id"] = request_id or "invalid"
        row["operation"] = operation or "invalid"
        row["request_document_sha256"] = digest(document)
        row["transport"] = transport
        return note_fallback(row)

    if document.get("schema") != REQUEST_SCHEMA:
        return bound(local_request_receipt(request_id or "invalid", operation or "invalid", "REFUSED_REQUEST", "REQUEST_SCHEMA_MISMATCH"))
    if not REQUEST_ID.fullmatch(request_id):
        return bound(local_request_receipt(request_id or "invalid", operation or "invalid", "REFUSED_REQUEST", "REQUEST_ID_INVALID"))
    payload = document.get("payload", {})
    if not isinstance(payload, dict):
        return bound(local_request_receipt(request_id, operation, "REFUSED_REQUEST", "PAYLOAD_NOT_OBJECT"))
    if operation not in TRIO_OPERATIONS:
        # The bounded trio is the whole external capability (v26.9.25 section 7);
        # generic MCP and actuate are refused before any transport is dialed.
        return bound(local_request_receipt(request_id, operation or "invalid", "REFUSED_REQUEST", "OPERATION_UNSUPPORTED"))

    if transport == "github-actions":
        row = local_request_receipt(
            request_id,
            operation,
            "BLOCKED",
            "TRANSPORT_DELEGATED",
            "explicit fallback selection: this request executes via the "
            ".github/workflows/xaas-runtime-proxy.yml request/receipt relay, not locally",
        )
        row["replay"] = "git commit xaas-runtime/requests/<request_id>.json and let the xaas-runtime workflow execute it"
        return bound(row)

    if transport == "wss":
        if tunnel is None:
            tunnel = resolve_tunnel()
        missing = missing_tunnel_config(tunnel.url)
        if missing:
            return bound(local_request_receipt(
                request_id,
                operation,
                "BLOCKED",
                "IRREDUCIBLE_TRANSPORT_CONFIG",
                "missing environment: " + ",".join(missing),
            ))
        shape_error = tunnel_config_error(tunnel)
        if shape_error:
            return bound(local_request_receipt(request_id, operation, "BLOCKED", "IRREDUCIBLE_TRANSPORT_CONFIG", shape_error))
        exchange = wss_exchange(tunnel)
        authenticated = bool(tunnel.token)
    else:
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
        exchange = None
        authenticated = None

    if operation == "fabric.probe":
        row = probe(target, timeout, exchange=exchange, authenticated=authenticated)
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
        row = submit_run(target, args, exchange=exchange, authenticated=authenticated)
    elif operation == "epoch.receipts":
        epoch_id = payload.get("epoch_id")
        try:
            normalized = str(uuid.UUID(str(epoch_id)))
        except (ValueError, TypeError, AttributeError):
            return bound(local_request_receipt(request_id, operation, "REFUSED_REQUEST", "EPOCH_ID_INVALID"))
        row = read_receipts(target, normalized, timeout, exchange=exchange, authenticated=authenticated)
    else:  # pragma: no cover - membership enforced above
        return bound(local_request_receipt(request_id, operation, "REFUSED_REQUEST", "OPERATION_UNSUPPORTED"))

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
                    row = execute_request_document(
                        document, None, args.timeout, args.require_config,
                        transport=getattr(args, "transport", "http"),
                        tunnel=resolve_tunnel(url=getattr(args, "tunnel_url", None))
                        if getattr(args, "transport", "http") == "wss" else None,
                    )
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
    p.add_argument("--tunnel-url", help="override XAAS_TUNNEL_URL (ws:// or wss://)")
    p.add_argument(
        "--transport",
        choices=("http", "wss", "github-actions"),
        default="http",
        help="http = direct HTTP (default); wss = direct WebSocket tunnel "
        "(target architecture); github-actions = explicit request/receipt relay fallback",
    )
    p.add_argument("--timeout", type=float, default=15.0)
    p.add_argument(
        "--require-config",
        dest="require_config_global",
        action="store_true",
        help="refuse to fall back to the localhost default; missing transport config is BLOCKED[IRREDUCIBLE_TRANSPORT_CONFIG]",
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
    request = sub.add_parser("request", help="execute one bounded request document over the selected transport")
    request.add_argument("--request", type=Path, required=True)
    request.add_argument("--receipt", type=Path, required=True)
    request.add_argument("--require-config", action="store_true")
    return p


def delegated_transport_receipt(command: str) -> dict[str, Any]:
    row = local_request_receipt(
        "direct",
        command,
        "BLOCKED",
        "TRANSPORT_DELEGATED",
        "explicit fallback selection: operations execute via the "
        ".github/workflows/xaas-runtime-proxy.yml request/receipt relay, not locally",
    )
    row.pop("request_id")
    row.pop("operation")
    row["transport"] = "github-actions"
    row["replay"] = "git commit xaas-runtime/requests/<request_id>.json and let the xaas-runtime workflow execute it"
    return row


def wss_direct_target(args: argparse.Namespace, command: str) -> tuple[TunnelTarget, str | None]:
    """Returns (tunnel, error_receipt_detail). A typed config edge precedes any dial."""
    tunnel = resolve_tunnel(url=getattr(args, "tunnel_url", None))
    missing = missing_tunnel_config(tunnel.url)
    if missing:
        return tunnel, "missing environment: " + ",".join(missing)
    shape_error = tunnel_config_error(tunnel)
    if shape_error:
        return tunnel, shape_error
    return tunnel, None


def local_transport_row(command: str, detail: str, transport: str) -> dict[str, Any]:
    row = local_request_receipt("direct", command, "BLOCKED", "IRREDUCIBLE_TRANSPORT_CONFIG", detail)
    row.pop("request_id")
    row.pop("operation")
    row["transport"] = transport
    row["target_source"] = "wss"
    row["replay"] = f"python3 scripts/xaas-runtime.py --transport {transport} --require-config {command}"
    return row


def main(argv: list[str] | None = None) -> int:
    p = parser()
    args = p.parse_args(argv)
    target = resolve_target(url=args.url)
    if args.require_config_global and args.command != "request":
        # Direct (non-relay) path: an absent target is a configuration edge, not a
        # network edge. Never let the localhost default masquerade as NETWORK.
        if args.transport == "wss":
            missing = missing_tunnel_config(args.tunnel_url)
            detail = "missing environment: " + ",".join(missing) if missing else None
        else:
            missing = missing_config(args.url)
            detail = "missing environment: " + ",".join(missing) if missing else None
        if missing:
            row = local_request_receipt(
                "direct",
                args.command,
                "BLOCKED",
                "IRREDUCIBLE_TRANSPORT_CONFIG",
                detail,
            )
            row.pop("request_id")
            row.pop("operation")
            row["target_source"] = "wss" if args.transport == "wss" else target_source(args.url)
            row["replay"] = (
                f"python3 scripts/xaas-runtime.py --transport wss --require-config {args.command}"
                if args.transport == "wss"
                else f"python3 scripts/xaas-runtime.py --require-config {args.command}"
            )
            print(json.dumps(row, indent=2, sort_keys=True))
            return exit_code(row)
    if args.transport == "github-actions" and args.command != "request":
        row = delegated_transport_receipt(args.command)
        print(json.dumps(row, indent=2, sort_keys=True))
        return exit_code(row)
    if args.transport == "wss" and args.command == "mcp":
        # The tunnel carries only the bounded trio; generic MCP (and therefore the
        # actuate DO verb) stays on the direct HTTP surface.
        row = local_request_receipt(
            "direct",
            args.command,
            "REFUSED_REQUEST",
            "TRIO_ONLY_TRANSPORT",
            "the wss tunnel carries only fabric.probe, run.submit, epoch.receipts; "
            "generic MCP and actuate are not relayable",
        )
        row["standing"] = "REFUSED_REQUEST"
        row["transport"] = "wss"
        row.pop("request_id")
        row.pop("operation")
        row["replay"] = "python3 scripts/xaas-runtime.py --transport http mcp tools/list"
        print(json.dumps(row, indent=2, sort_keys=True))
        return exit_code(row)
    exchange = None
    authenticated = None
    if args.transport == "wss":
        tunnel, detail = wss_direct_target(args, args.command)
        if detail is not None:
            row = local_transport_row(args.command, detail, "wss")
            print(json.dumps(row, indent=2, sort_keys=True))
            return exit_code(row)
        exchange = wss_exchange(tunnel)
        authenticated = bool(tunnel.token)
    if args.command == "probe":
        row = probe(target, args.timeout, exchange=exchange, authenticated=authenticated)
        if args.transport == "wss":
            row = note_fallback(row)
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
        if args.transport != "wss":
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
            if args.command == "submit-run":
                row = submit_run(target, args, exchange=exchange, authenticated=authenticated)
            else:
                row = read_receipts(target, args.epoch_id, args.timeout, exchange=exchange, authenticated=authenticated)
            if args.transport == "wss":
                row = note_fallback(row)
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
