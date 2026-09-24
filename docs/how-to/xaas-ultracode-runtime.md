# XaaS Ultracode runtime bridge

This repository can talk to the existing XaaS Ultracode execution fabric from a
restricted ChatGPT cloud container without installing Elixir, Bun, or ZCode
first. The bridge is `scripts/xaas-runtime.py`; it uses only Python's standard
library and emits a machine-readable receipt for every operation.

## Boundary

The implementation reuses the existing cross-repository contract instead of
creating another execution plane:

```text
ChatGPT cloud
  -> scripts/xaas-runtime.py
  -> XaaS /internal-api/execution/*
  -> Xaas.Ultracode lease/run/receipt domain
  -> provider = zcode
  -> zcode gall-work claim -> construct -> close
```

The observed contract used for this implementation was:

- `seanchatmangpt/xaas@7659b10e22a806da98295ed799602a6f809562d9`:
  Bearer-gated `POST /internal-api/execution/mcp`,
  `POST /internal-api/execution/runs`, and
  `GET /internal-api/execution/epochs/:epoch_id/receipts`.
- `seanchatmangpt/zcode-cli@32093eafc2f1cc202ace2cded38b72ec1f81e4ba`:
  native `zcode gall-work` using the same JSON-RPC MCP endpoint and
  `XAAS_MCP_URL` / `XAAS_MCP_TOKEN` resolution.

Ultracode is the `Xaas.Ultracode.*` execution fabric inside `xaas`; it is
not a separate repository.

## Configure

Inject the endpoint and token into the cloud runtime. Do not commit either:

```bash
export XAAS_MCP_URL='https://<xaas-host>/internal-api/execution/mcp'
export XAAS_MCP_TOKEN='<bearer-token>'
```

The token remains XaaS authority. The bridge never prints it and never places it
in replay commands.

## Verify the live fabric contract

```bash
python3 scripts/xaas-runtime.py --require-config probe
```

From a cloud agent (ChatGPT Cloud or Claude Code Cloud) always pass
`--require-config`. Without it the client falls back to the local-dev default
`http://localhost:4000/...`, and an unconfigured container would report
`BLOCKED[NETWORK]` (connection refused) instead of the real edge. With it, a
missing `XAAS_MCP_URL` / `XAAS_MCP_TOKEN` is reported as
`BLOCKED[IRREDUCIBLE_TRANSPORT_CONFIG]` before any network call. Every direct
receipt records `target_source` (`flag`, `env`, or `default`).

`probe` performs MCP `initialize` and `tools/list`, then requires:

- server name `xaas-ultracode-lease`;
- protocol `2025-03-26`;
- `claim_next`, `heartbeat`, `admit_tool`, `record_provider_event`,
  `close_candidate`, `refuse`, and `actuate`.

A reachable matching endpoint is `ALIVE` for the **transport contract only**.
Authentication, network, protocol, and contract mismatches are typed separately.

## Submit work for ZCode

The customer-facing XaaS submission route requires an org-carrying internal API
token. A legacy shared token can use internal/admin routes but XaaS deliberately
refuses run submission with HTTP 403.

```bash
python3 scripts/xaas-runtime.py submit-run \
  --goal 'implement the admitted work order' \
  --exact-subject 'seanchatmangpt/example@<sha>' \
  --verifier-suite '<registered-suite>'
```

The provider defaults to `zcode`, so the created running epoch is claimable by
the existing ZCode `gall-work` lifecycle. If `--worktree` is supplied, it
must be an absolute path meaningful on the **XaaS host**, not a path in the
ChatGPT cloud container.

A successful HTTP submission is reported as `PARTIAL_ALIVE` with
`downstream_standing: UNKNOWN`. It does not claim that ZCode ran, committed,
verified, or closed the epoch.

## Observe receipts

Use the `epoch_id` returned by submission:

```bash
python3 scripts/xaas-runtime.py receipts <epoch-uuid>
```

This calls XaaS's lawful receipt-read surface. The response can contain the
sealed Ultracode receipts, but the bridge does not reinterpret a receipt-shaped
payload as execution proof.

## Direct MCP interaction

Inspection and lease-protocol calls use the same JSON-RPC surface:

```bash
python3 scripts/xaas-runtime.py mcp tools/list
python3 scripts/xaas-runtime.py mcp tools/call \
  --tool heartbeat \
  --arguments '{"lease_token":"<lease-token>"}'
```

The `actuate` verb crosses into the XaaS DO kernel and is therefore locally
fenced as well as server-side fenced. It requires an explicit acknowledgement:

```bash
python3 scripts/xaas-runtime.py mcp tools/call \
  --tool actuate \
  --allow-do \
  --arguments '{"lease_token":"<lease>","resource":"<registered>","action":"<registered>","idempotency_key":"<key>","input":{}}'
```

Without `--allow-do`, no network request is sent and the bridge emits
`REFUSED_AUTHORITY / EXPLICIT_DO_ACK_REQUIRED`. Supplying the flag still grants
nothing: XaaS must independently admit the lease and registered resource/action.

## GitHub relay for egress-blocked ChatGPT containers

When the current ChatGPT execution container cannot reach XaaS over outbound
TCP/DNS, direct HTTP is not a lawful substitute for observed connectivity.
This repository therefore reuses its existing GitHub request/receipt transport
pattern:

```text
ChatGPT GitHub connector
  -> xaas-runtime/requests/<request_id>.json
  -> .github/workflows/xaas-runtime-proxy.yml
  -> protected GitHub Environment "xaas-runtime"
  -> XaaS Ultracode
  -> xaas-runtime/receipts/<request_id>.receipt.json
```

Configure `XAAS_MCP_URL` and `XAAS_MCP_TOKEN` as secrets on the
`xaas-runtime` GitHub Environment. The workflow's secret-bearing surface is
strictly smaller than the direct client: it accepts only `fabric.probe`,
`run.submit`, and `epoch.receipts`. Generic `tools/call` and `actuate`
are not relay operations.

Request documents use schema
`chatgpt-cloud.xaas-runtime-request/1`; the filename must equal
`<request_id>.json`. Every parsed request is digest-bound into its operation
receipt. See [the transport directory](../../xaas-runtime/README.md) for exact
request examples.

A GitHub workflow run is transport, not standing. `run.submit` remains
`PARTIAL_ALIVE` with downstream `UNKNOWN` until ZCode actually claims the
epoch, the configured verifier court passes, XaaS seals a receipt, and replay
confirms the exact subject.

## Local court

The bridge has no third-party Python dependencies:

```bash
python3 -m py_compile scripts/xaas-runtime.py
python3 -m unittest -v tests/test_xaas_runtime.py
```

The 16-case test court covers contract discovery, missing-tool falsification, Bearer
propagation without token leakage, ZCode-default submission, receipt reads,
typed authentication/tool refusals, network blockage, successful
`PARTIAL_ALIVE` submission exit semantics, the local `actuate` fence, and
GitHub-relay request admission/refusal behavior.

## Evidence ceiling

A local fixture passing proves the client/protocol implementation. A live
`probe` proves only the configured transport contract. Run submission proves
only that XaaS admitted the submission. Subject `ALIVE` requires the real
ZCode/Ultracode execution, independent verification, sealed receipt, and replay
at the exact admitted subject.
