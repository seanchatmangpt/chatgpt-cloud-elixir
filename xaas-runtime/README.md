# XaaS runtime transport

`xaas-runtime/requests/` and `xaas-runtime/receipts/` are the GitHub transport
for ChatGPT cloud environments whose container cannot open outbound network
connections to XaaS directly.

The canonical runtime protocol remains XaaS Ultracode. These files are only
request/receipt transport:

```text
ChatGPT cloud GitHub connector
  -> xaas-runtime/requests/<request_id>.json
  -> GitHub Actions environment: xaas-runtime
  -> scripts/xaas-runtime.py
  -> XaaS Ultracode
  -> xaas-runtime/receipts/<request_id>.receipt.json
```

The `xaas-runtime` GitHub Environment is the authority boundary. Configure
`XAAS_MCP_URL` and `XAAS_MCP_TOKEN` as environment secrets there. The XaaS
token should be a scoped DB-backed `InternalApiToken`; `run.submit` requires an
org-carrying token. Request files contain no credentials.

The secret-bearing workflow accepts only three operations. Generic MCP and the
`actuate` DO verb are intentionally not relayable.

## Probe

```json
{
  "schema": "chatgpt-cloud.xaas-runtime-request/1",
  "request_id": "20260924T210000Z-probe",
  "operation": "fabric.probe",
  "payload": {}
}
```

## Submit work for the existing ZCode worker lifecycle

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

## Read one epoch's sealed receipts

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

The request filename must equal `<request_id>.json`. Request resolution is
`scripts/xaas-runtime-requests.sh` (shared by both workflow jobs): paths must be
flat `xaas-runtime/requests/<id>.json` regular files (no subdirectories, `..`,
or symlinks), and a request that already has a receipt is **never
re-executed**. Push re-runs, job re-runs, edits, and re-dispatches are no-ops.
To retry after a BLOCKED receipt (for example once the environment secrets are
configured), commit a NEW `request_id`. A new-branch or force-push (unresolvable
`before`) falls back to every unreceipted request, not to an empty set.

Receipts never carry the XaaS host: `endpoint` is `<scheme>://<redacted-host>/<path>`
plus `endpoint_sha256` for equality checks. The client refuses URL userinfo and
never follows redirects (which would replay the bearer). Only the execute step
receives `XAAS_MCP_URL` / `XAAS_MCP_TOKEN`, and workflow inputs reach bash only
through `env`. The workflow is scoped to
flat `xaas-runtime/requests/*.json` paths, serializes receipt writes per branch,
and commits machine-readable receipts back to the triggering branch. Workflow
success is transport evidence only; subject `ALIVE` still requires the real
Ultracode/ZCode court and replay at the exact admitted subject.
