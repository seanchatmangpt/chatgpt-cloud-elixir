# MCP Tools at `/mcp`

`control-plane/`'s Phoenix router mounts `AshAi.Mcp.Router` at `/mcp` (pipeline
`:api`, requiring `Authorization: Bearer $OCEL_INGEST_TOKEN` — the same token used
for OCEL ingestion; there is no separate MCP-specific credential). Exactly 6 tools
are exposed, listed below.

## Tool table

| Tool | Ash action wrapped | Domain | Arguments | Return shape |
|---|---|---|---|---|
| `list_qualifications` | `Qualification` `:read` (default read) | `ChatGPTCloud.ProcessIntelligence` | Standard Ash query args (filter/sort/limit via AshAi's query encoding) | List of `Qualification` records: `qualification_key`, `run_key`, `subject_repo`, `subject_sha`, `kind`, `standing`, `result` (map), `requested_at`/`started_at`/`completed_at`, `state` (state-machine field) |
| `list_cost_observations` | `CostObservation` `:read` | `ChatGPTCloud.ProcessIntelligence` | Same query-arg convention | List of `CostObservation` records: `observation_key`, `run_key`, `category`, `estimated_cost` (AshMoney), `basis` (map), `observed_at` |
| `read_dfcm_memory` | `MemoryRecord` `:read` (manual, live GitHub call, no DB) | `ChatGPTCloud.DfcmMemory` | Ash query filter/args; filterable by `key`/`kind`/`cell`/`standing`/`tags` | List of `MemoryRecord`: `key`, `title`, `kind`, `cell`, `standing`, `tags`, `body`, `metadata`, `item_id`, `content_id`, `is_archived`, `updated_at` |
| `upsert_dfcm_memory` | `MemoryRecord` generic action `:upsert_record` | `ChatGPTCloud.DfcmMemory` | `key` (required); `title`, `kind`, `cell`, `standing`, `tags` ([string]), `body`, `metadata` (map) — all optional | `%{action: "created" \| "updated", item_id, content_id, title, metadata, project}` |
| `snapshot_dfcm_project` | `MemoryRecord` generic action `:snapshot` | `ChatGPTCloud.DfcmMemory` | none | `%{project: %{owner, number, id, title, url}, item_count, memory_item_count, truncated}` |
| `list_project_items` | `MemoryRecord` generic action `:project_items` | `ChatGPTCloud.DfcmMemory` | `max_items` (int, optional); `types` ([`ISSUE`\|`PULL_REQUEST`\|`DRAFT_ISSUE`], optional); `include_archived` (bool, default `false`) | List of `%{item_id, type, is_archived, content_id, title, body, url, number, repository, state, labels: [{name, color}], assignees: [{login}], field_values: {field_name => value}}` |

## Domain-level tool declarations

`ChatGPTCloud.ProcessIntelligence`'s domain module (`domain.ex`) also declares AshAi
`tools` for `list_qualifications`/`list_cost_observations` at the domain level,
matching the router's allowlist. No other domain resource (agents, events, objects,
receipts, conformance results, refusals, process variants, `SecretCredential`) is
exposed as an MCP tool — those are reachable only via AshAdmin (`/admin`, HTTP Basic
Auth), the JSON:API (`/api/json`), or GraphQL (`/graphql`).

## Auth

All 6 tools share the same gate as raw OCEL ingestion: `Authorization: Bearer
$OCEL_INGEST_TOKEN`, checked by `ChatGPTCloudWeb.OcelAuth` via
`Plug.Crypto.secure_compare`. Anyone holding that token can call every tool listed
here, read/write DfCM memory, and also reach `/graphql` and `/api/json`.

See also: `docs/reference/project-memory-protocol.md` for the underlying GitHub
Project v2 operations `read_dfcm_memory`/`upsert_dfcm_memory`/
`snapshot_dfcm_project`/`list_project_items` correspond to; `docs/reference/env-vars.md`
for `OCEL_INGEST_TOKEN`.
