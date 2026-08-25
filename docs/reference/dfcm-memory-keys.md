# DfCM Memory Key Convention

Stable key naming convention used by records written to GitHub Project v2
`seanchatmangpt/2` via the project-memory protocol (both the Python proxy transport
and the Elixir/MCP transport share the same key space — see
`docs/reference/project-memory-protocol.md` and `docs/reference/mcp-tools.md`).

## Key table

| Key | Writer | Purpose |
|---|---|---|
| `dfcm/frontier/current` | PORTFOLIO | Current admitted capability frontier and newly opened adjacency |
| `dfcm/ledger/current` | all cells | Accumulated capability/observation/selection/replication/merge edges |
| `dfcm/measure/latest` | MEASURE | Latest observation set, sensors, `E`, measurement ERRC delta |
| `dfcm/explore/latest` | EXPLORE | Latest non-dominated candidates, hypergraph delta, `E2` |
| `dfcm/select/latest` | SELECT/DEVELOP | Selected Pareto portfolio, capital allocation, `Y`, preserved alternatives |
| `dfcm/implement/latest` | IMPLEMENT/QUALIFY | Canonical primitives, consumer census, qualification, `R` |
| `dfcm/portfolio/latest` | PORTFOLIO | Autocatalytic generation state, `C`, `H5`, next-cycle seeds |

Immutable historical records are also appended for durable evidentiary/learning
value, using the pattern `dfcm/run/<cell>/<UTC-timestamp>/<head-sha>` — not one card
per commit.

## Metadata multiplier fields

Records for the cells above carry a `metadata` map with named multiplier fields. The
README's own worked request-schema example uses six: `E`, `E2`, `Y`, `R`, `C`, `M`
(e.g. `{"E": 4, "E2": 5, "Y": 3, "R": 6, "C": 2, "M": 2}`). Note this naming is not
perfectly consistent across the repo's own examples: both
`project-memory/examples/dfcm-frontier-upsert.json` and the `dfcm/portfolio/latest`
row in `project-memory/README.md` use `H5` in the same conceptual slot where the
request-schema example uses `M` — the field name is not fully pinned to a single
canonical spelling across all examples currently in the repo.

## Read-before-manufacture / write-after-manufacture order

Mandatory read order before a cell starts work: (1) `dfcm/frontier/current`, (2)
`dfcm/ledger/current`, (3) the cell's own prior `latest` record, (4) the preceding
cell's `latest` record, (5) any other relevant queried memories. A write to the
cell's own `latest` key is mandatory after every run, success or not — even a no-op
run is recorded. Skipping either the read or the write makes that cell's run
`BUILD_BROKEN` for its memory-loop contract, independent of whether the underlying
manufacturing work itself succeeded.

See also: `docs/reference/project-memory-protocol.md` for the operations used to
read/write these keys; `docs/reference/status-vocabulary.md` for the standing values
a record's `standing` field may hold; `docs/explanation/` for the DfCM cell model and
the "crown equation" rationale.
