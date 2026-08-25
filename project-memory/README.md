# GitHub Project v2 Memory Proxy

This directory turns GitHub Project **`seanchatmangpt/2`** into a bounded, persistent memory surface for ChatGPT cloud work.

The architecture is deliberately indirect:

```text
ChatGPT / scheduled cell
        |
        | create request JSON through connected GitHub CRUD
        v
project-memory/requests/<request-id>.json
        |
        | push-triggered GitHub Action
        v
scripts/project_memory_proxy.py
        |
        | authenticated GitHub GraphQL using PROJECTS_TOKEN when present
        v
GitHub Project v2 #2
        |
        | typed result
        v
project-memory/receipts/<request-id>.receipt.json
```

The **Project is canonical memory**. Request and receipt files are transport/evidence only.

## Authority

The proxy is hard-scoped to:

- owner: `seanchatmangpt`
- project number: `2`

Raw GraphQL is not accepted. The workflow exposes only the operations below. Requests targeting another project are `REFUSED[PROJECT_SCOPE_VIOLATION]`.

For user-project write authority, configure an Actions secret named **`PROJECTS_TOKEN`** containing a GitHub credential that can read and write that user Project v2. The workflow attempts the repository `GITHUB_TOKEN` as a capability probe when the secret is absent; if GitHub does not authorize the user project, the receipt records `BLOCKED[IRREDUCIBLE_AUTHORITY]` rather than pretending the mutation succeeded.

Secrets are never written into receipts or logs. Receipts record only the token *source class*.

## Operations

The bounded protocol is:

- `project.snapshot` — inspect the configured project and its items.
- `memory.create` — create a new memory record as a Project draft issue; duplicate keys are refused.
- `memory.read` — fetch one memory record by stable key.
- `memory.update` — update an existing memory record by key.
- `memory.upsert` — create or update a memory record by key.
- `memory.query` — query memory records by text, kind, standing, cell, and tags.
- `memory.archive` — archive a memory item while preserving it.
- `memory.delete` — delete a memory item from the project.

Memory records are Project draft issues so the memory store does not need to manufacture repository issues. A machine-readable metadata envelope is embedded in the draft body; human-readable body text remains readable in the Project UI.

## Request schema

```json
{
  "request_id": "20260825T071500Z-portfolio-frontier",
  "operation": "memory.upsert",
  "project": {"owner": "seanchatmangpt", "number": 2},
  "payload": {
    "record": {
      "key": "dfcm/frontier/current",
      "title": "DfCM current frontier",
      "kind": "dfcm.frontier",
      "cell": "PORTFOLIO",
      "standing": "ALIVE",
      "tags": ["dfcm", "frontier", "shared-memory"],
      "body": "Exact machine-readable or Markdown frontier payload.",
      "metadata": {
        "E": 4,
        "E2": 5,
        "Y": 3,
        "R": 6,
        "C": 2,
        "head_sha": "..."
      }
    }
  }
}
```

Every request needs a unique `request_id`. The memory `key` is separately stable and supports updates across runs.

## DfCM shared-memory convention

The five manufacturing cells should use Project #2 as **cross-run and cross-cell memory**, not as a task checklist.

Recommended stable keys:

| Key | Writer | Purpose |
| --- | --- | --- |
| `dfcm/frontier/current` | PORTFOLIO | Current admitted capability frontier and newly opened adjacency. |
| `dfcm/ledger/current` | all cells | Accumulated capability/observation/selection/replication/merge edges. |
| `dfcm/measure/latest` | MEASURE | Latest observation set, sensors, `E`, and measurement ERRC delta. |
| `dfcm/explore/latest` | EXPLORE | Latest non-dominated candidates, hypergraph delta, and `E2`. |
| `dfcm/select/latest` | SELECT/DEVELOP | Selected Pareto portfolio, capital allocation, `Y`, preserved alternatives. |
| `dfcm/implement/latest` | IMPLEMENT/QUALIFY | Canonical primitives, consumer census, qualification and `R`. |
| `dfcm/portfolio/latest` | PORTFOLIO | Autocatalytic generation state, `C`, `H5`, and next-cycle seeds. |

Append immutable historical memory only when it has durable evidentiary or learning value, for example `dfcm/run/<cell>/<UTC>/<head>`. Do not explode the Project into one card per commit. Commits remain receipts in Git; Project memory stores **capability state, frontier state, learned constraints, reusable decisions, falsifiers, and cross-run continuity**.

### Read-before-manufacture

Each cell should begin by reading:

1. `dfcm/frontier/current`;
2. `dfcm/ledger/current`;
3. its own `latest` record;
4. the immediately preceding cell's `latest` record;
5. relevant queried memories for repositories/capabilities it is about to touch.

Project memory is an input to observation, never unquestioned truth. Bind reused memory to current GitHub evidence and classify stale or contradicted memories rather than silently acting on them.

### Write-after-manufacture

Each cell should upsert its `latest` record with:

- exact repositories/refs/heads observed and changed;
- observed/admitted/executed/verified/inferred distinctions;
- new capabilities and newly reachable combinations;
- ERRC before/after delta;
- cell multiplier (`E`, `E2`, `Y`, `R`, or `C`);
- cross-repo dependency/unlock edges;
- falsifiers and repaired defects;
- qualification/merge receipts;
- next-cell handoff;
- exact standing.

PORTFOLIO additionally upserts `dfcm/frontier/current` and the shared ledger after each materially frontier-changing generation.

## DfCM × ERRC rule

Project memory should **increase the reachable frontier**, not become bureaucratic inventory.

- **Eliminate** rediscovery, duplicate private state, stale parallel truths, and repeated reasoning already captured with evidence.
- **Reduce** context reconstruction latency, uncertainty about prior runs, cross-cell handoff loss, and distance from evidence to next lawful action.
- **Raise** information persistence, provenance, graph connectivity, exact-subject continuity, reusable learning, falsifier retention, and frontier visibility.
- **Create** new memory-derived compositions, cross-run hypotheses, missing sensors, reusable packs, verifier courts, consumer families, and factories-for-factories.

A memory read should be treated as an opportunity generator:

```text
memory + current evidence -> delta -> new adjacency -> manufacture -> new memory
```

The crown is not "the board is updated." The crown is that persistent knowledge causes **more lawful novel capability to become reachable in the next run than would have been reachable without the memory**.

## Receipts and standings

Every request emits a receipt containing request identity, operation, project identity when resolved, result/error, token source class, and standing.

- `ALIVE` means the exact Project query/mutation executed and returned successfully.
- `REFUSED` means the bounded protocol rejected the request.
- `BLOCKED` with reason `IRREDUCIBLE_AUTHORITY` means the available credential could not access the user project.
- `UNKNOWN` means transport/API evidence was insufficient.
- `BUILD_BROKEN` means the proxy itself violated its execution contract.

Workflow green status is not by itself proof of Project mutation; the receipt is the operation-level evidence.
