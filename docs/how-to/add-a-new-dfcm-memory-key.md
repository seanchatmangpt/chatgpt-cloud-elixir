# How to add a new DfCM memory key

DfCM memory keys are a naming convention over `memory.*` records stored as
Project draft issues on `seanchatmangpt/2`, not a schema enforced by code.
The existing convention:

| Key | Writer | Purpose |
|---|---|---|
| `dfcm/frontier/current` | PORTFOLIO | Current admitted capability frontier and newly opened adjacency |
| `dfcm/ledger/current` | all cells | Accumulated capability/observation/selection/replication/merge edges |
| `dfcm/measure/latest` | MEASURE | Latest observation set, sensors, `E`, measurement ERRC delta |
| `dfcm/explore/latest` | EXPLORE | Latest non-dominated candidates, hypergraph delta, `E2` |
| `dfcm/select/latest` | SELECT/DEVELOP | Selected Pareto portfolio, capital allocation, `Y`, preserved alternatives |
| `dfcm/implement/latest` | IMPLEMENT/QUALIFY | Canonical primitives, consumer census, qualification, `R` |
| `dfcm/portfolio/latest` | PORTFOLIO | Autocatalytic generation state, `C`, `H5`/`M`, next-cycle seeds |
| `dfcm/run/<cell>/<UTC>/<head>` | any cell | Immutable historical run record, appended only for durable evidentiary/learning value |

## Steps to add a new key

1. Pick a namespace consistent with the table above: `dfcm/<cell-or-topic>/latest`
   for the current-state slot of a cell, or `dfcm/run/<cell>/<UTC>/<head>`
   for an immutable historical record. Don't create a new top-level prefix
   unless the key genuinely represents a new kind of durable cross-run
   state, not a one-off task note.

2. Before writing anything, read in this order (mandatory per the repo's
   read-before-manufacture contract):
   1. `dfcm/frontier/current`
   2. `dfcm/ledger/current`
   3. your own cell's existing `latest` record (if any)
   4. the preceding cell's `latest` record
   5. any other relevant queried memories

   Skipping this makes the write `BUILD_BROKEN` for the memory-loop
   contract, independent of whether the underlying manufacturing work
   succeeded.

3. Write the record via a request file
   (`project-memory/requests/<request-id>.json`) with `operation:
   "memory.upsert"`:

   ```json
   {
     "request_id": "20260825T140000Z-explore-latest",
     "operation": "memory.upsert",
     "project": {"owner": "seanchatmangpt", "number": 2},
     "payload": {
       "record": {
         "key": "dfcm/explore/<your-topic>/latest",
         "title": "...",
         "kind": "...",
         "cell": "EXPLORE",
         "standing": "ALIVE",
         "tags": ["dfcm", "explore"],
         "body": "...",
         "metadata": {"E": 4, "E2": 5, "Y": 3, "R": 6, "C": 2, "M": 2}
       }
     }
   }
   ```

   Or, via the MCP transport, call `upsert_dfcm_memory` with `key`
   (required) plus `title`, `kind`, `cell`, `standing`, `tags`, `body`,
   `metadata`.

4. `memory.upsert` always resolves the current record by key first — it is
   never a blind overwrite. `memory.update` specifically merges into the
   *existing* metadata dict rather than replacing it wholesale (only `tags`
   is fully replaced, deduped and sorted), so a partial update can't
   accidentally wipe unrelated metadata fields.

5. Commit/push the request file, or call the MCP tool directly — both
   converge on the same Project #2 records; neither transport is
   authoritative, the Project itself is.

## The metadata multipliers

Records commonly carry six named multipliers as `metadata` fields: `E`,
`E2`, `Y`, `R`, `C`, and either `M` or `H5` — the repo's own examples are not
perfectly consistent on which of the last two names is used (the README's
schema example uses `M`; `project-memory/examples/dfcm-frontier-upsert.json`
and the `dfcm/portfolio/latest` table row use `H5` for the same conceptual
slot). Pick one and be consistent within your own cell's records rather than
treating either name as more canonical than the other.

## See also

- [Query the full-fidelity project.items data instead of just memory records](query-full-fidelity-project-items.md)
- `docs/reference/` — full `project_memory_proxy.py` operation/request/result
  schemas
- `docs/explanation/` — the crown equation and why persistent memory is the
  actual payoff, not "the board is updated"
