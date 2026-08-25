# How to query the full-fidelity project.items data instead of just memory records

`memory.read`/`memory.query` (and the MCP `read_dfcm_memory` tool) only see
records that carry the `<!-- chatgpt-project-memory:v1 ... -->` marker. Use
`project.items` (Python transport) or `list_project_items` (MCP transport)
when you need the raw board state — every Issue, Pull Request, and Draft
Issue on `seanchatmangpt/2`, including custom field values — regardless of
whether it's a memory record.

## Via the Python/Action transport

1. Write a request file to `project-memory/requests/<request-id>.json`:

   ```json
   {
     "request_id": "20260825T120000Z-inspect-board",
     "operation": "project.items",
     "project": {"owner": "seanchatmangpt", "number": 2},
     "payload": {
       "types": ["ISSUE", "PULL_REQUEST", "DRAFT_ISSUE"],
       "include_archived": false,
       "max_items": 500
     }
   }
   ```

   `types`, `include_archived`, and `max_items` are all optional. Note that
   type/archived filtering happens client-side after the fetch — the
   GraphQL `items()` connection has no server-side filter beyond
   pagination.

2. Commit and push it under `project-memory/requests/**/*.json` (or trigger
   via `workflow_dispatch` with `request_path`). This fires
   `.github/workflows/project-memory-proxy.yml`.

3. Read the result from `project-memory/receipts/<request-id>.receipt.json`.
   The `result.items` array has this shape per item:

   ```json
   {
     "item_id": "...",
     "is_archived": false,
     "type": "ISSUE",
     "content": {
       "id": "...", "title": "...", "body": "...", "url": "...",
       "number": 42, "repository": "...", "state": "OPEN",
       "labels": [{"name": "...", "color": "..."}],
       "assignees": [{"login": "..."}]
     },
     "field_values": {"<Field Name>": "value"}
   }
   ```

   `field_values` is a flattened `{field_name: value}` map decoded from the
   GraphQL fieldValues union (text/number/date/single-select/iteration).

## Via the MCP transport

Call the `list_project_items` tool at `/mcp` (bearer-token authenticated
with `OCEL_INGEST_TOKEN`) with the same optional arguments:
`max_items` (int), `types` (list of `ISSUE`/`PULL_REQUEST`/`DRAFT_ISSUE`),
`include_archived` (bool, default `false`). This is the only one of the 4
DfCM MCP tools that reads the whole board rather than just memory-marked
records.

## When to use this instead of memory.query / read_dfcm_memory

- You need to see a Pull Request or repository Issue that was manually added
  to the Project, not written as a memory record.
- You need custom field values (status, iteration, etc.) that aren't part of
  the memory-record schema.
- You're debugging why a `memory.read` by key returned
  `REFUSED[MEMORY_NOT_FOUND]` and want to check what's actually on the board.

For everything else — reading/writing the structured DfCM cell state itself
(`dfcm/frontier/current`, `dfcm/measure/latest`, etc.) — use
`memory.read`/`memory.upsert` or `read_dfcm_memory`/`upsert_dfcm_memory`
instead; they're purpose-built for the memory-record schema and don't
require you to filter a full board dump client-side.

## See also

- [Add a new DfCM memory key](add-a-new-dfcm-memory-key.md)
- [Add a new AshAi MCP tool](add-a-new-ashai-mcp-tool.md)
- `docs/reference/` — full `project_memory_proxy.py` operation reference
- `docs/explanation/` — why the Project itself, not either transport, is
  authoritative
