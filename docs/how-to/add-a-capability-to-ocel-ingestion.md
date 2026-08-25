# How to add a new capability to the OCEL ingestion schema

`POST /api/v1/ocel/batches` (`ChatGPTCloudWeb.IngestController.create/2` →
`ChatGPTCloud.ProcessIntelligence.Ingestor.ingest/1`) accepts envelopes with
`schema: "chatgpt-cloud-ocel/1"`. Use this guide when a producer needs to
report a new kind of data the current envelope doesn't cover.

## Before changing anything

Ingestion writes directly via `Repo.insert_all`/upsert against table names —
it deliberately bypasses the Ash resource action pipeline entirely, even
though the OCEL tables (`Agent`, `Run`, `Event`, ...) are modeled as full Ash
resources. Those Ash resources exist purely as read-side/admin-side
projections (`actions: defaults [:read]` only). Any change to what
ingestion accepts belongs in `Ingestor`, not in an Ash changeset/action.

## Steps

1. Decide whether the new data fits an existing top-level envelope key
   (`events`, `objects`, `object_relationships`, `receipts`,
   `conformance_results`, `refusals`, `process_variants`) or needs a new
   one:

   ```jsonc
   {
     "schema": "chatgpt-cloud-ocel/1",
     "producer": { "agent_id": "...", "run_id": "...", "status": "running", ... },
     "events": [ { "id": "...", "activity": "...", "sequence": 1, "timestamp": "...", "lifecycle": "complete", "standing": "UNKNOWN", "authority_domain": "OBSERVE", "digest": "...", "payload": {}, "objects": [...] } ],
     "objects": [ ... ],
     "object_relationships": [ ... ],
     "receipts": [ ... ],
     "conformance_results": [ ... ],
     "refusals": [ { "type": "REFUSAL_TYPE", "reason": "...", "timestamp": "..." } ],
     "process_variants": [ { "id": "...", "name": "...", "model_type": "...", "model_digest": "...", "payload": {} } ]
   }
   ```

2. If extending an existing key (e.g. adding a new optional field to
   `events[]`), update `Ingestor`'s normalization logic for that key so the
   new field is read and mapped to the corresponding Ecto table/column, and
   add or update the matching Ecto migration in `control-plane/priv/repo/migrations/`
   if a new column is needed.

3. If the new data doesn't fit any existing key, add a new top-level
   optional key, following the pattern of the existing ones: optional,
   defaulting to `[]`/absent, normalized in `Ingestor`, persisted via
   `Repo.insert_all` with an appropriate `on_conflict` (`:replace` for
   upsertable natural-key data like agents/runs, `:nothing` for
   append-only data like events, matching the idempotency behavior of the
   existing keys).

4. If the new data should be readable, add a corresponding Ash resource
   (read-only, `actions: defaults [:read]` per `ResourceHelpers`) under
   `ChatGPTCloud.ProcessIntelligence.Resources`, and decide whether it
   should be surfaced via AshAdmin only, or also via JSON:API/GraphQL/MCP
   (see [Add a new AshAi MCP tool](add-a-new-ashai-mcp-tool.md) if so).

5. Keep the standing vocabulary consistent: `event.standing` accepts
   `UNKNOWN | PARTIAL_ALIVE | ALIVE | BLOCKED | BUILD_BROKEN | UNSUPPORTED`,
   plus any string prefixed `REFUSED_`. Reuse this vocabulary rather than
   inventing a new one for a new field.

6. Test locally:

   ```bash
   cd control-plane
   mix setup
   OCEL_INGEST_TOKEN=dev-ocel-token mix phx.server
   ```

   ```bash
   curl -X POST http://localhost:4000/api/v1/ocel/batches \
     -H 'content-type: application/json' \
     -H 'authorization: Bearer dev-ocel-token' \
     -d '{ "schema": "chatgpt-cloud-ocel/1", "producer": {"agent_id": "local-agent", "run_id": "run-001"}, "events": [ ... your new field ... ] }'
   ```

   Confirm a `202 Accepted` response with `accepted_events`,
   `duplicate_events`, `run_key`, `agent_key`, `standing: "ALIVE"` — a `422`
   with `standing: "BLOCKED"` means normalization rejected the envelope.

7. `scripts/emit-ocel.py` generates this envelope shape from CLI flags and
   is used both by control-plane CI (`control-plane-ci.yml`, as a real
   producer self-test) and by the `process-intelligence` capsule's
   `harness/emit-ocel.py` — if you add a new field producers are expected to
   send, consider updating this generator too so it stays a realistic
   reference producer.

8. Format-check and run tests before committing:

   ```bash
   mix format --check-formatted
   mix test
   ```

## Bumping the schema version

The envelope's `schema` field is checked for the exact literal string
`"chatgpt-cloud-ocel/1"`. If a change is not backward-compatible (removes or
repurposes a field rather than adding an optional one), treat this as a new
schema version — the current code only recognizes `chatgpt-cloud-ocel/1`, so
introducing `chatgpt-cloud-ocel/2` requires `Ingestor` to explicitly branch
on schema version, not silently assume the new shape.

## See also

- `docs/reference/` — the full envelope field reference, standing
  vocabulary table
- `docs/explanation/` — why ingestion bypasses the Ash action pipeline
  while reads go through it
