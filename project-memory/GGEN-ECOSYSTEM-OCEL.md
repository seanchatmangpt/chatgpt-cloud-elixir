# GGEN Ecosystem OCEL — Project #2 contract

`GGEN ECOSYSTEM OCEL` is the canonical process-state substrate for the five hourly manufacturing cells.

## Canonical correspondence

```text
Project #2 current state
  -> admitted RDF facts
  -> ggen-ecosystem-ocel-pack
  -> OCEL 2.0 execution log + Project-memory request
  -> consumer realization / qualification / merge
  -> Git + operation receipts
  -> wasm4pm / wasm4pm-compat analysis
  -> next Project #2 frontier
```

GGEN emits process evidence. It does not perform process discovery, conformance, fitness, precision, or variant analysis. Those remain owned by wasm4pm/wasm4pm-compat.

## Canonical memory identity

The only current-state key for the manufacturing process is:

```text
ggen/ecosystem/ocel/current
```

`ocel/v2/revops/current` may remain as a RevOps projection/history input, but it is not an alternate current manufacturing truth. A request claiming the GGEN Ecosystem OCEL contract under another key is refused by `scripts/project_memory_bus.py`.

Required record identity:

- kind: `ggen.ecosystem.ocel.current`
- tags: `ggen`, `ocel`, `manufacturing`, `project2`
- metadata: `run_id`, `ocel_digest`, `manufacturing_ladder=U->G->O->Q->M`, `ggen_first=true`, `process_analysis_owner=wasm4pm`

## Manufacturing ladder

```text
U = compatible/admissible universe
G = GGEN-manufactured realization
O = OCEL-observed/exercised consequence
Q = exact-head qualified
M = merged/default-lineage assimilated
```

`G` without `O` is not exercised. `O` without `Q` is not qualified. `Q` without `M` is not assimilated.

## Schedule law

Every hourly cell must:

1. read `ggen/ecosystem/ocel/current` before manufacturing;
2. search/compose GGEN marketplace capital before handwritten consumer implementation;
3. represent material run transitions as admitted manufacturing events/objects;
4. use `ggen-ecosystem-ocel-pack` to manufacture the OCEL and Project-memory projections where its runtime is available;
5. bind consumer changes to exact repository/base/head and upstream GGEN primitive;
6. keep process intelligence outside GGEN and the Elixir control plane;
7. upsert the canonical key after the run with its OCEL digest and exact standing;
8. let CELL5 replay/close the `U -> G -> O -> Q -> M` graph before crowning the wave.

## Independent verifier

`project_memory_bus.py` does not trust the generator merely because the request exists. It independently refuses:

- parallel Project-memory keys;
- wrong record kind/tags;
- missing run/cell/standing identity;
- missing OCEL digest;
- a manufacturing ladder other than `U->G->O->Q->M`;
- `ggen_first != true`;
- a process-analysis owner other than `wasm4pm`.

The verifier never manufactures OCEL and never analyzes a process. Its only authority is transport admission/refusal before Project #2 actuation.
