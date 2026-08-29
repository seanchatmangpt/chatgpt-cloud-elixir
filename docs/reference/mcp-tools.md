# MCP Tools at `/mcp`

`control-plane/`'s Phoenix router mounts `AshAi.Mcp.Router` at `/mcp` (pipeline
`:api`, requiring `Authorization: Bearer $OCEL_INGEST_TOKEN` — the same token used
for OCEL ingestion; there is no separate MCP-specific credential). The router's
allowlist (`router.ex`) currently forwards 20 tools in total. The table below
documents the 10 declared by `ChatGPTCloud.ProcessIntelligence` plus
`ChatGPTCloud.DfcmMemory`'s four foundational memory tools; see "Domain-level tool
declarations" below for the remaining 10 `ChatGPTCloud.DfcmMemory` semantic/graph
projection tools, which are forwarded by the router but not yet tabulated here.

## Tool table

| Tool | Ash action wrapped | Domain | Arguments | Return shape |
|---|---|---|---|---|
| `list_qualifications` | `Qualification` `:read` (default read) | `ChatGPTCloud.ProcessIntelligence` | Standard Ash query args (filter/sort/limit via AshAi's query encoding) | List of `Qualification` records: `qualification_key`, `run_key`, `subject_repo`, `subject_sha`, `kind`, `standing`, `result` (map), `requested_at`/`started_at`/`completed_at`, `state` (state-machine field) |
| `list_cost_observations` | `CostObservation` `:read` | `ChatGPTCloud.ProcessIntelligence` | Same query-arg convention | List of `CostObservation` records: `observation_key`, `run_key`, `category`, `estimated_cost` (AshMoney), `basis` (map), `observed_at` |
| `list_conformance_results` | `ConformanceResult` `:read` (default read) | `ChatGPTCloud.ProcessIntelligence` | Same query-arg convention | List of `ConformanceResult` records: `result_key`, `run_key`, `model_key`, `fitness` (decimal), `standing`, `payload` (map), `observed_at` |
| `list_refusals` | `Refusal` `:read` (default read) | `ChatGPTCloud.ProcessIntelligence` | Same query-arg convention | List of `Refusal` records: `refusal_key`, `run_key`, `refusal_type`, `reason`, `payload` (map), `observed_at` |
| `list_process_variants` | `ProcessVariant` `:read` (default read) | `ChatGPTCloud.ProcessIntelligence` | Same query-arg convention | List of `ProcessVariant` records: `variant_key`, `name`, `model_type`, `model_digest`, `payload` (map), `first_seen_at`, `last_seen_at` |
| `list_swarm_teams` | `SwarmTeam` `:read` (default read) | `ChatGPTCloud.ProcessIntelligence` | Same query-arg convention; `velocity`/`completed_work_item_count` are Ash aggregates loadable via the query's `load` argument | List of `SwarmTeam` records: `team_key`, `name`, `inserted_at`, `updated_at`, plus (when loaded) `completed_work_item_count` (integer) and `velocity` (sum of completed `SwarmWorkItem.priority` for that team) |
| `read_dfcm_memory` | `MemoryRecord` `:read` (manual, live GitHub call, no DB) | `ChatGPTCloud.DfcmMemory` | Ash query filter/args; filterable by `key`/`kind`/`cell`/`standing`/`tags` | List of `MemoryRecord`: `key`, `title`, `kind`, `cell`, `standing`, `tags`, `body`, `metadata`, `item_id`, `content_id`, `is_archived`, `updated_at` |
| `upsert_dfcm_memory` | `MemoryRecord` generic action `:upsert_record` | `ChatGPTCloud.DfcmMemory` | `key` (required); `title`, `kind`, `cell`, `standing`, `tags` ([string]), `body`, `metadata` (map) — all optional | `%{action: "created" \| "updated", item_id, content_id, title, metadata, project}` |
| `snapshot_dfcm_project` | `MemoryRecord` generic action `:snapshot` | `ChatGPTCloud.DfcmMemory` | none | `%{project: %{owner, number, id, title, url}, item_count, memory_item_count, truncated}` |
| `list_project_items` | `MemoryRecord` generic action `:project_items` | `ChatGPTCloud.DfcmMemory` | `max_items` (int, optional); `types` ([`ISSUE`\|`PULL_REQUEST`\|`DRAFT_ISSUE`], optional); `include_archived` (bool, default `false`) | List of `%{item_id, type, is_archived, content_id, title, body, url, number, repository, state, labels: [{name, color}], assignees: [{login}], field_values: {field_name => value}}` |

## Domain-level tool declarations

`ChatGPTCloud.ProcessIntelligence`'s domain module (`domain.ex`) declares AshAi
`tools` for `list_qualifications`, `list_cost_observations`, `list_conformance_results`,
`list_refusals`, `list_process_variants`, and `list_swarm_teams` at the domain level,
matching the router's allowlist. No other domain resource (agents, events, objects,
event/object relationships, receipts, `SecretCredential`, `SwarmAgent`, the Ash-native
`SwarmWorkItem`) is exposed as an MCP tool — those are reachable only via AshAdmin
(`/admin`, HTTP Basic Auth), the JSON:API (`/api/json`), or GraphQL (`/graphql`).

`ChatGPTCloud.DfcmMemory`'s domain module additionally declares 10 more semantic/graph
projection tools (`inspect_project_semantics`, `project_property_graph`,
`query_project_graph`, `project_relational_tables`, `project_semantic_triples`,
`project_jsonld`, `project_service_catalog`, `project_ocel`, `project_llm_context`,
`project_vision_2030`) that the router forwards but this table does not yet document
row-by-row — a pre-existing gap this pass did not close; see
`control-plane/lib/chatgpt_cloud_control_plane/dfcm_memory/domain.ex` for their exact
action bindings.

## Auth

> **Security:** `OCEL_INGEST_TOKEN` is the single credential securing four separate
> surfaces — OCEL ingestion, this MCP tool set (including the `upsert_dfcm_memory`
> write action), `/graphql`, and `/api/json`. There is no per-surface or read/write
> split: anyone holding this one token has full read/write reach across all four.
> Treat it with the same care as a database admin credential, not a scoped API key.

All 20 tools share the same gate as raw OCEL ingestion: `Authorization: Bearer
$OCEL_INGEST_TOKEN`, checked by `ChatGPTCloudWeb.OcelAuth` via
`Plug.Crypto.secure_compare`. Anyone holding that token can call every tool listed
here, read/write DfCM memory, and also reach `/graphql` and `/api/json`.

See also: `docs/reference/project-memory-protocol.md` for the underlying GitHub
Project v2 operations `read_dfcm_memory`/`upsert_dfcm_memory`/
`snapshot_dfcm_project`/`list_project_items` correspond to; `docs/reference/env-vars.md`
for `OCEL_INGEST_TOKEN`.
