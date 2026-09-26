# XaaS runtime transport

`xaas-runtime/` carries the client surface for the XaaS Ultracode execution
fabric. The target architecture (v26.9.25 section 7) is a **direct WSS
transport**: ephemeral cloud coordination must not depend on GitHub Actions.

```text
CloudWorker
  --WSS/443--> XaaS (Xaas.Tunnel) --> BRCE --> ZCode
```

GitHub Actions remains a **fallback transport / evidence path only** — it is
not the target runtime architecture.

The canonical runtime protocol remains XaaS Ultracode. The bounded external
capability is exactly the trio `fabric.probe`, `run.submit`, `epoch.receipts`
— never unrestricted `actuate`, never generic MCP. The mandatory sequence is
`probe -> admit -> submit -> execute -> sealedReceipt -> replay`; a ZCode
execution claim requires the live probe to have succeeded first and the
execution receipt to be sealed afterward.

## Transport selection (`scripts/xaas-runtime.py --transport`)

| transport | role | config | standing when unconfigured |
|---|---|---|---|
| `wss` | **primary / target** | `XAAS_TUNNEL_URL` (`ws://` or `wss://`), `XAAS_TUNNEL_TOKEN` | `BLOCKED[IRREDUCIBLE_TRANSPORT_CONFIG]` before any dial |
| `http` | direct HTTP surface (`XAAS_MCP_URL` / `XAAS_MCP_TOKEN`) | same tokens as the direct client | `BLOCKED[IRREDUCIBLE_TRANSPORT_CONFIG]` with `--require-config` |
| `github-actions` | explicit fallback: request/receipt relay | protected `xaas-runtime` GitHub Environment secrets | `BLOCKED[TRANSPORT_DELEGATED]` locally, by design |

R25-015: a transport failure is typed, never a subject failure. A wss dial
that cannot connect yields `BLOCKED` with reason `TRANSPORT` (handshake 401/403
yield `REFUSED_AUTHENTICATION`/`REFUSED_AUTHORITY`), and the receipt records
`fallback_transport: github-actions` — the only condition under which the
fallback is selected.

```bash
# Primary: direct tunnel dial
python3 scripts/xaas-runtime.py --transport wss --require-config probe

# Explicit fallback only after a typed wss transport failure:
python3 scripts/xaas-runtime.py --transport github-actions probe
```

The wss client is stdlib-only (RFC 6455 over `socket`/`ssl`): one WebSocket
dial per request envelope, client frames always masked, 4 MiB frame cap,
ping/pong and close handled, and the bearer token carried in the upgrade
handshake `Authorization` header. The tunnel envelope contract (implemented
by `Xaas.Tunnel` on the xaas side; server landing is tracked on the xaas
lane) is:

```text
-> {"v":1,"kind":"http","method":"POST","path":"/internal-api/execution/mcp","headers":{...},"body":{...}}
<- {"v":1,"kind":"http_response","status":200,"body":{...}}
```

The bounded trio flow (probe -> admit -> submit -> execute -> sealedReceipt
-> replay) is identical across transports; only the wire changes.

## Request documents

Requests use schema `chatgpt-cloud.xaas-runtime-request/1`; the filename must
equal `<request_id>.json`. Request resolution is
`scripts/xaas-runtime-requests.sh`: paths must be flat
`xaas-runtime/requests/<id>.json` regular files (no subdirectories, `..`, or
symlinks), and a request that already has a receipt is **never re-executed**.
Push re-runs, job re-runs, edits, and re-dispatches are no-ops. To retry
after a BLOCKED receipt, commit a NEW `request_id`. A new-branch or
force-push (unresolvable `before`) falls back to every unreceipted request,
not to an empty set.

### Probe

```json
{
  "schema": "chatgpt-cloud.xaas-runtime-request/1",
  "request_id": "20260924T210000Z-probe",
  "operation": "fabric.probe",
  "payload": {}
}
```

### Submit work for the existing ZCode worker lifecycle

```json
{
  "schema": "chatgpt-cloud.xaas-runtime-request/1",
  "request_id": "20260924T210100Z-example",
  "operation": "run.submit",
  "payload": {
    "goal": "Implement the admitted work order",
    "provider": "zcode",
    "exact_subject": "seanchatmangpt/example@0123456789abcdef0123456789abcdef01234567",
    "verifier_suite": "registered-suite"
  }
}
```

`provider` is restricted to `zcode`. `exact_subject` is mandatory. A successful
submission receipt is `PARTIAL_ALIVE` with downstream standing `UNKNOWN`: it
proves XaaS admitted the run, not that ZCode executed or verified it.

A `worktree` may be supplied only when it is an absolute, existing Git
repository path visible on the XaaS host. Omit it otherwise; XaaS permits a nil
worktree and will not manufacture a cloud-container path into server authority.

### Read one epoch's sealed receipts

```json
{
  "schema": "chatgpt-cloud.xaas-runtime-request/1",
  "request_id": "20260924T210200Z-read",
  "operation": "epoch.receipts",
  "payload": {
    "epoch_id": "11111111-1111-1111-1111-111111111111"
  }
}
```

## Authority boundary and secrets

The wss transport's authority-bearing inputs are `XAAS_TUNNEL_URL` and
`XAAS_TUNNEL_TOKEN`; they are environment-resolved only, never committed,
never printed, and never placed in replay commands. On the fallback path the
`xaas-runtime` GitHub Environment is the authority boundary: configure
`XAAS_MCP_URL` and `XAAS_MCP_TOKEN` as environment secrets there. The XaaS
token should be a scoped DB-backed `InternalApiToken`; `run.submit` requires
an org-carrying token. Request files contain no credentials.

The secret-bearing surfaces accept only the bounded trio. Generic MCP and the
`actuate` DO verb are intentionally not relayable (`wss` refuses them with
`REFUSED_REQUEST[TRIO_ONLY_TRANSPORT]` before any dial).

Receipts never carry the XaaS host: `endpoint` is `<scheme>://<redacted-host>/<path>`
plus `endpoint_sha256` for equality checks. The client refuses URL userinfo
and never follows redirects (which would replay the bearer). The fallback
workflow is scoped to flat `xaas-runtime/requests/*.json` paths, serializes
receipt writes per branch, and commits machine-readable receipts back to the
triggering branch. Workflow success is transport evidence only; subject
`ALIVE` still requires the real Ultracode/ZCode court and replay at the exact
admitted subject.

## Qualification court

The relay, the direct client, and the wss transport are permanently exercised
by `tests/test_xaas_runtime.py`, including the mock RFC 6455 tunnel court
(probe success, submit `PARTIAL_ALIVE`, receipts round trip, trio fence
before dial, unreachable-tunnel `BLOCKED[TRANSPORT]`, missing tunnel config,
handshake 401 typing, userinfo refusal, request-over-wss receipt writes),
request-path admission, replay suppression, redirect refusal, endpoint
redaction, protocol-shape validation, explicit DO fencing, and
missing-config typing. The hardened runtime court is:

```bash
python3 -m py_compile scripts/xaas-runtime.py
python3 -m pytest tests/test_xaas_runtime.py -q
# or: python3 tests/test_xaas_runtime.py
```

The v26.9.25 wss lane observed 50/50 tests passing (pytest exit 0). Live
tunnel standing is `PARTIAL_ALIVE` by design: the client, its court, and the
envelope contract are merged here, while the `Xaas.Tunnel` server side lands
via the xaas lane — until that endpoint is deployed, wss probes correctly
produce typed `BLOCKED[TRANSPORT]` receipts naming the github-actions
fallback, without misreporting a subject failure.
