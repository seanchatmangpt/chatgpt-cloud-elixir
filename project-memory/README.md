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

## Second transport: the Claude junction (MCP)

The flow above is the ChatGPT-side transport. There is a second, symmetric transport for
Claude (or any MCP client): `control-plane`'s `ChatGPTCloud.DfcmMemory` Ash domain
(`control-plane/lib/chatgpt_cloud_control_plane/dfcm_memory/`) wraps the same Project
`seanchatmangpt/2` — same hard-scoped owner/number, same body-encoding marker
(`<!-- chatgpt-project-memory:v1 ... -->`) as `scripts/project_memory_proxy.py` — and
exposes it as `AshAi` tools over the existing `/mcp` endpoint
(`control-plane/lib/chatgpt_cloud_control_plane_web/router.ex`):

```text
ChatGPT scheduled cell                          Claude (MCP client)
        |                                                |
        | request JSON + push-triggered Action           | read_dfcm_memory /
        v                                                 | upsert_dfcm_memory /
scripts/project_memory_proxy.py                           | snapshot_dfcm_project
        |                                                 v
        `---------------> GitHub Project v2 #2 <----------'
                      (seanchatmangpt/2, shared)
```

Both transports write and read the *same* records — a memory key either side upserts is
immediately legible to the other on its next read-before-manufacture check. Neither
transport is authoritative over the other; the Project itself is. Tools:

- `read_dfcm_memory` — `MemoryRecord.read`, filterable by key/kind/cell/standing/tags.
- `upsert_dfcm_memory` — `MemoryRecord.upsert_record`, always resolves the current record
  for `key` first (never a blind overwrite).
- `snapshot_dfcm_project` — live Project identity + item/memory-record counts, read-only.

Implementation follows the [wrap-external-APIs Ash pattern](https://ash.hexdocs.pm/wrap-external-apis.html):
`MemoryRecord` is an `Ash.Resource` on `Ash.DataLayer.Simple` with a manual `:read` action
(`ChatGPTCloud.DfcmMemory.ManualRead`) that calls the GitHub GraphQL API directly (no new
dependency — Erlang's built-in `:httpc`, mirroring the Python proxy's stdlib-only
`urllib` client) and applies the Ash query to the resulting in-memory list.

## Authority

The proxy is hard-scoped to:

- owner: `seanchatmangpt`
- project number: `2`

Raw GraphQL is not accepted. The workflow exposes only the operations below. Requests targeting another project are `REFUSED[PROJECT_SCOPE_VIOLATION]`.

For user-project write authority, configure an Actions secret named **`PROJECTS_TOKEN`** containing a GitHub credential that can read and write that user Project v2. The workflow attempts the repository `GITHUB_TOKEN` as a capability probe when the secret is absent; if GitHub does not authorize the user project, the receipt records `BLOCKED[IRREDUCIBLE_AUTHORITY]` rather than pretending the mutation succeeded.

Secrets are never written into receipts or logs. Receipts record only the token *source class*.

## Commit hygiene

The proxy workflow commits `project-memory/receipts/` once per run (see "Commit receipts
to transport branch" in `.github/workflows/project-memory-proxy.yml`) — that one-commit-
per-run discipline is load-bearing, not incidental: Project #2 is one shared mutable
control plane, and the workflow's `concurrency` group plus rebase-retry loop depend on
each run landing as exactly one commit to stay race-free. It is not going away.

What changed: the commit subject used to be the literal, content-free string `receipt:
Project v2 memory proxy` on every run, indistinguishable from every other run in `git
log`. At the automation cadence this proxy actually runs at, that produced hundreds of
identical-looking subjects per branch (see `docs/swarm-noise-budget.md` for the full
accounting). The subject is now data-bearing — `receipt: Project v2 memory proxy (<N>:
<request-basenames>)` — so the commit says what it carries without needing `git show`.

For an already-landed run of the old-style commits on a branch you control,
`scripts/compact_project_memory_receipts.py --apply` squashes a trailing run into one
commit (dry-run by default; never touches a shared branch without `--force`-equivalent
intent from you — it's a local history rewrite, push it with care).

## Operations

The bounded protocol is:

- `project.snapshot` — inspect the configured project and its items.
- `project.items` — read-only, full-fidelity read of every item on the project (not just
  memory-marked ones): title, body, url, state, labels, assignees, and every custom
  ProjectV2 field value (text/number/date/single-select/iteration), decoded into a flat
  `{field_name: value}` map per item. Payload: `{"types": ["ISSUE", "PULL_REQUEST",
  "DRAFT_ISSUE"], "include_archived": false, "max_items": 500}` (all keys optional; `types`
  defaults to all three, filtered client-side after fetch since the GraphQL `items()`
  connection has no server-side type/archived filter beyond pagination). Result:
  `{"items": [{"item_id", "is_archived", "type", "content": {"id", "title", "body", "url",
  "number", "repository", "state", "labels": [{"name","color"}], "assignees": ["login"]},
  "field_values": {"<Field Name>": <value>}}], "item_count", "truncated"}`.
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
        "M": 2,
        "commit_count": 0,
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

### Manufacturing cadence and phase-change baseline

The prior per-cell baseline was 50 meaningful semantic commits/run (250/hour across the
five cells). That baseline was a *floor*, not a target, and floors that are never revisited
become ceilings by habit. The standing target is a **1000x phase change** on that floor:

```text
50 -> 500 -> 5,000 -> 50,000 meaningful semantic commits/run (search expansion, not a hard gate)
```

`50,000` is the phase-change reference point (1000x of the old 50), not a quota to pad
toward with trivial or duplicate commits — the ERRC discipline below (Eliminate rediscovery,
Raise provenance) still governs what counts as meaningful. A cell that has real lawful work
should keep expanding past its previous run's count; a cell that has exhausted real lawful
work reports that honestly (`UNKNOWN`/`BLOCKED`, not a padded number) rather than
manufacturing volume for its own sake. The multiplier stack (`E`, `E2`, `Y`, `R`, `C`, `M`)
is what should carry a cell from the old floor toward the new phase-change reference, not a
raw commit-count target pursued directly.

### Read-before-manufacture (mandatory, every run)

Every cell **must** check Project #2 before doing any manufacturing work, with no
conditional skip. "Should read" is upgraded to "does not begin manufacturing until it has
read." Order:

1. `dfcm/frontier/current`;
2. `dfcm/ledger/current`;
3. its own `latest` record;
4. the immediately preceding cell's `latest` record;
5. relevant queried memories for repositories/capabilities it is about to touch.

Project memory is an input to observation, never unquestioned truth. Bind reused memory to
current GitHub evidence and classify stale or contradicted memories rather than silently
acting on them. A `memory.query`/`memory.read` failure (`BLOCKED`/`UNKNOWN`) is itself an
observation — record it and proceed from live GitHub evidence alone; it does not authorize
skipping the check on the *next* run.

### Write-after-manufacture (mandatory, every run)

Every cell **must** upsert Project #2 after manufacturing, whether or not it produced new
commits — a no-new-work run is itself a fact worth recording (falsifier, exhausted search
space, blocked edge), not a silent no-op. "Should upsert" is upgraded to "does not consider
the run complete until it has written." Each cell upserts its `latest` record with:

- exact repositories/refs/heads observed and changed;
- observed/admitted/executed/verified/inferred distinctions;
- new capabilities and newly reachable combinations;
- ERRC before/after delta;
- cell multiplier (`E`, `E2`, `Y`, `R`, `C`, or `M`);
- commit count this run vs. the 50->500->5,000->50,000 cadence above;
- cross-repo dependency/unlock edges;
- falsifiers and repaired defects;
- qualification/merge receipts;
- next-cell handoff;
- exact standing.

PORTFOLIO additionally upserts `dfcm/frontier/current` and the shared ledger after each
materially frontier-changing generation.

A cell that skips either the before-check or the after-write for a given run is
`BUILD_BROKEN` for that run's memory-loop contract, independent of whether its manufacturing
work itself succeeded.

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
