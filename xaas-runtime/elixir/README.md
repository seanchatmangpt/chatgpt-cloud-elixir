# XaaS runtime fabric client (Elixir)

Standalone Mix project (`:xaas_runtime_client`, namespace `ChatGPTCloud.Xaas.*`) that
drives one run through the XaaS bounded runtime fabric, protocol `xaas-fabric/1`,
under `/internal-api/fabric`. It is the Elixir twin of `scripts/xaas-runtime.py`:
same environment names (`XAAS_MCP_URL`, `XAAS_MCP_TOKEN`), same `classify_http`
table, same canonical JSON and sha256.

```text
probe -> admit -> submit -> leased -> sealed -> replayed
GET /probe  POST /admit  POST /runs (idempotency_key)  GET /epochs/:id/receipts?wait_ms=&after=
POST /actuate -> 403 REFUSED(authority_ceiling:actuate)   (never emitted by this client)
```

Capabilities are exactly `fabric.probe`, `run.submit`, `epoch.receipts`. A probe that
advertises anything else is `UNSUPPORTED(CONTRACT_MISMATCH)`.

## Modules

- `Transport` behaviour and `Transport.Http` (`:httpc`, `autoredirect: false`,
  `verify: :verify_peer`, URL userinfo refused).
- `Fabric`: pure state machine (`new/2`, `next/1`, `apply/2`, `classify/2`, `resume/2`).
- `Receipt`: canonical JSON and sha256, byte-identical to Python `canonical_json`.
- `Runner`: the only impure loop; journals to `xaas-runtime/journal/<key>.json`.
- `mix xaas_runtime.fabric`: writes `xaas-runtime/receipts/<ts>-fabric.receipt.json`.

## Run

```bash
cd xaas-runtime/elixir
HEX_OFFLINE=1 mix deps.get
mix format --check-formatted && mix compile --warnings-as-errors && mix test
XAAS_MCP_URL=http://localhost:4100/internal-api/execution/mcp XAAS_MCP_TOKEN=... \
  mix xaas_runtime.fabric --goal "fabric live leg" --idempotency-key live-001
```

## Evidence ceiling

Tests run against a contract fixture server (`test/support/contract_server.ex`): a
real Bandit listener on loopback serving the contract as written there. That proves
the client against the written contract, not against XaaS. The live XaaS leg is the
contract test; until it runs, client-to-XaaS standing is `UNKNOWN`.

The golden receipt `test/fixtures/receipt_golden.json` with digest
`test/fixtures/receipt_golden.sha256` is checked by both `test/receipt_golden_test.exs`
and `tests/test_xaas_runtime.py`, and is the parity target for xaas `Xaas.Tunnel.Receipt`.
