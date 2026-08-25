# Project Memory Proxy Protocol

`scripts/project_memory_proxy.py` implements a bounded protocol of exactly 9
operations (`ALLOWED_OPERATIONS`, `scripts/project_memory_proxy.py:25-35`) against
GitHub Project v2 `seanchatmangpt/2`. This is the complete request/result reference
for every operation. All requests are JSON files under `project-memory/requests/`
matching the envelope below; results are written to
`project-memory/receipts/<id>.receipt.json`.

## Request envelope (all operations)

```json
{
  "request_id": "20260825T071500Z-portfolio-frontier",
  "operation": "memory.upsert",
  "project": {"owner": "seanchatmangpt", "number": 2},
  "payload": { }
}
```

`project.owner`/`project.number` must equal `seanchatmangpt`/`2` exactly — any other
value is refused (`REFUSED[PROJECT_SCOPE_VIOLATION]`).

## Receipt shape (all operations)

```json
{
  "schema": "...",
  "request_path": "...",
  "request_id": "...",
  "operation": "...",
  "observed_at": "ISO8601",
  "token_source": "PROJECTS_TOKEN secret",
  "standing": "ALIVE | REFUSED | BLOCKED | UNKNOWN | BUILD_BROKEN",
  "reason": "...",
  "result": { },
  "error": null,
  "request_digest_basis": "..."
}
```

## Operations

### `project.snapshot`

Read-only. Inspect the project plus a summarized item list.

- Payload: `{"max_items": 500}` (optional)
- Result: `{"project": {owner, number, id, title, url}, "items": [{item_id, content_id, type, is_archived, title, memory_key, memory_kind, memory_updated_at}], "item_count", "memory_item_count", "truncated"}`

### `project.items`

Read-only, full-fidelity read of every item on the board (not just memory-marked
ones).

- Payload: `{"types": ["ISSUE", "PULL_REQUEST", "DRAFT_ISSUE"], "include_archived": false, "max_items": 500}` (all optional; type/archived filtering is client-side after fetch)
- Result: `{"items": [{item_id, is_archived, type, content: {id, title, body, url, number, repository, state, labels: [{name, color}], assignees: [login]}, field_values: {"<Field Name>": value}}], "item_count", "truncated"}`
- `field_values` is a flattened `{field_name: value}` map decoded from the GraphQL fieldValues union (text/number/date/single-select/iteration) by `flatten_field_values` (`scripts/project_memory_proxy.py:73-103`)

### `memory.create`

Creates a new memory record as a Project draft issue. Refuses on duplicate key.

- Payload: `{"record": {"key": "...", "title": "...", "kind": "...", "cell": "...", "standing": "ALIVE", "tags": [...], "body": "...", "metadata": {}}}`
- Result: `{item_id, content_id, title, body, is_archived, metadata}`
- Failure: `REFUSED[DUPLICATE_MEMORY_KEY]` if `key` already exists

### `memory.read`

Fetch one record by key.

- Payload: `{"key": "dfcm/frontier/current", "include_archived": true}`
- Result: same shape as `memory.create`, or `REFUSED[MEMORY_NOT_FOUND]`

### `memory.update`

Update an existing record by key. Metadata is merged into the existing record's
metadata dict (a partial update cannot wipe unrelated metadata fields); `tags` is
fully replaced (deduped and sorted), not merged.

- Payload: `{"key": "...", "record": {...}}`
- Result: same shape as `memory.create`

### `memory.upsert`

Create-or-update by key; always resolves the current record first — never a blind
overwrite.

- Payload: same shape as `memory.create`
- Result: `{"action": "created" | "updated", "record": {...}}`
- Real example: `project-memory/examples/dfcm-frontier-upsert.json`

### `memory.query`

Filter by text (title/body/metadata substring, casefolded), `kind`, `standing`,
`cell`, `tags` (AND or OR via `match_all_tags`).

- Payload: `{"text": "...", "kind": "...", "standing": "...", "cell": "...", "tags": [...], "match_all_tags": false, "limit": 50, "max_scan": 5000}` (`limit` default 50, max 500; `max_scan` default 5000)
- Result: `{"records": [...], "matched", "scanned", "truncated"}`, sorted by `updated_at` descending

### `memory.archive`

Archives the Project item via `archiveProjectV2Item`, preserving the record.
Idempotent if already archived.

- Payload: `{"key": "..."}`
- Result: archived record shape

### `memory.delete`

Hard delete via `deleteProjectV2Item`.

- Payload: `{"key": "..."}`
- Result: `{"key", "deleted_item_id"}`

## Memory record body encoding

Records are stored as ProjectV2 **draft issues**, not repository issues. The
metadata envelope is a base64url-encoded JSON blob inside an HTML comment marker at
the top of the draft body, followed by human-readable Markdown:

```
<!-- chatgpt-project-memory:v1 <base64url(canonical-sorted-JSON)> -->
<human-readable body text>
```

Canonicalization: recursively key-sorted JSON, matching
`json.dumps(value, sort_keys=True, separators=(",",":"))` on the Python side and the
Elixir side's `canonical_json/1`.

## Token resolution order (workflow-side)

`PROJECTS_TOKEN` secret → `GH_TOKEN` secret → `GH_PAT` secret → `GITHUB_PAT` secret →
repository `GITHUB_TOKEN` fallback. Only the token *source class* string (e.g.
`"PROJECTS_TOKEN secret"`) is ever recorded in a receipt — never the token value.

See also: `docs/reference/status-vocabulary.md` for the standing values a receipt can
carry; `docs/reference/dfcm-memory-keys.md` for the memory key naming convention;
`docs/reference/mcp-tools.md` for the Elixir/MCP-side transport
(`read_dfcm_memory`/`upsert_dfcm_memory`/`snapshot_dfcm_project`/
`list_project_items`) covering a subset of these operations over the same store.
