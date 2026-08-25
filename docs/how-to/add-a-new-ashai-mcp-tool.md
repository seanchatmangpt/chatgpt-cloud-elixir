# How to add a new AshAi MCP tool

The `/mcp` endpoint (`control-plane/lib/chatgpt_cloud_control_plane_web/router.ex`,
forwarding to `AshAi.Mcp.Router`) currently exposes exactly 6 tools:
`list_qualifications`, `list_cost_observations` (from the
`ChatGPTCloud.ProcessIntelligence` domain), and `read_dfcm_memory`,
`upsert_dfcm_memory`, `snapshot_dfcm_project`, `list_project_items` (from the
`ChatGPTCloud.DfcmMemory` domain). Each wraps a specific Ash action.

## Steps

1. Decide which domain the new tool belongs to:
   `ChatGPTCloud.ProcessIntelligence` (OCEL-derived read-only data) or
   `ChatGPTCloud.DfcmMemory` (live GitHub Project v2 wrapper, no local
   storage).

2. Define the underlying Ash action first, if it doesn't exist yet:
   - A **read** action on an existing resource — follow the pattern of
     `Qualification`'s default `:read` action (standard Ash query args:
     filter/sort/limit).
   - A **generic action** for a mutation or a shaped read that doesn't map
     to CRUD — follow the pattern of `MemoryRecord`'s `:upsert_record`,
     `:snapshot`, or `:project_items` generic actions in
     `control-plane/lib/chatgpt_cloud_control_plane/dfcm_memory/`.

3. Add the action to the domain's `tools` block in `domain.ex` for that
   domain (e.g. `control-plane/lib/chatgpt_cloud_control_plane/process_intelligence/domain.ex`
   or `control-plane/lib/chatgpt_cloud_control_plane/dfcm_memory/domain.ex`) —
   this is what AshAi uses to decide the action is tool-eligible.

4. Add the tool name to the explicit allowlist that `router.ex` passes to
   `AshAi.Mcp.Router` at the `/mcp` mount. A domain-level `tools`
   declaration alone is not sufficient — the router's allowlist and the
   domain declaration must both name the tool, matching what the 6 existing
   tools do today.

5. Be aware of the shared-credential model before adding a tool that can
   mutate data: `/mcp` sits behind the same pipeline
   (`ChatGPTCloudWeb.OcelAuth`, `Authorization: Bearer $OCEL_INGEST_TOKEN`)
   as raw OCEL ingestion, `/graphql`, and `/api/json`. There is no
   MCP-specific credential tier — anyone holding `OCEL_INGEST_TOKEN` can call
   every tool you expose here.

6. Test the tool locally:

   ```bash
   cd control-plane
   mix setup
   OCEL_INGEST_TOKEN=dev-ocel-token mix phx.server
   ```

   Then call `/mcp` with the bearer token and confirm the new tool appears
   in the tool list and returns the expected shape.

7. Format-check before committing — CI (`format-control-plane.yml`) fails on
   any diff `mix format` would produce, not just on `--check-formatted`
   itself:

   ```bash
   mix format --check-formatted
   ```

## Notes on the existing pattern

- `read_dfcm_memory` covers ad-hoc querying via Ash filter args on the
  `MemoryRecord` resource; there is currently no `delete` or `archive` tool
  exposed over MCP even though the underlying `project_memory_proxy.py`
  transport supports `memory.archive`/`memory.delete` — if you're adding one
  of those, follow the `upsert_record.ex` generic-action pattern for the
  write path.
- `SecretCredential` is a real Ash resource in `control_resources.ex` but is
  deliberately **not** wired into any domain's `tools`/`json_api`/`graphql`
  blocks nor the MCP router allowlist — it is reachable only via AshAdmin.
  Do not add it to `/mcp` without a deliberate decision to do so.

## See also

- [Query the full-fidelity project.items data instead of just memory records](query-full-fidelity-project-items.md)
- [Add a new DfCM memory key](add-a-new-dfcm-memory-key.md)
- `docs/reference/` — the full 6-tool MCP signature table
- `docs/explanation/` — why ingestion bypasses the Ash action pipeline but
  reads go through it
