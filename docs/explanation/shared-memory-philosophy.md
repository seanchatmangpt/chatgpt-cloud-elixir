# Why GitHub Project v2 Is Cross-Agent Memory

`project-memory/` repurposes a GitHub Project v2 board (`seanchatmangpt/2`) as
durable, structured, cross-run memory for both ChatGPT scheduled cells and
Claude/MCP clients. This document explains the problem it solves, the contract
it enforces on every reader/writer, and — where the source material is precise
about it — the "crown equation" that motivates it. Where the underlying findings
are themselves imprecise, this document says so rather than inventing false
precision.

## The problem: repeated work with no shared state

Both ChatGPT's scheduled manufacturing cells and Claude, invoked via MCP, run
repeated work across many repos and many sessions, and by default each
invocation starts from nothing: no memory of what a prior run — its own or a
different cell's — already discovered, decided, or hit a wall on. Without
somewhere durable to persist that, every run is condemned to partially
rediscover what a previous run already knew, and no run can build on a prior
run's partial progress toward a larger, multi-run goal.

`project-memory/README.md` states the resulting principle directly, quoted
verbatim: the crown "is not 'the board is updated.' The crown is that
persistent knowledge causes more lawful novel capability to become reachable in
the next run than would have been reachable without the memory." Memory here is
explicitly not a bookkeeping artifact — it is instrumental. Its value is judged
by what it makes possible for the *next* run, not by its own existence.

## Why a GitHub Project v2 board specifically

A GitHub Project v2 board has several properties that make it a workable choice
for this role, though the underlying findings do not enumerate an explicit
"why not X" comparison against alternatives — this section reasons from the
properties actually used, not from a documented rejection of other options:

- It is durable and external to any single deploy or session — neither a
  ChatGPT scheduled cell nor a Claude session owns it, so neither can lose it by
  ending.
- It is human-inspectable directly in the GitHub UI, in addition to being
  machine-readable — a memory record stored as a Project draft issue carries
  both a machine-decodable metadata marker and ordinary human-readable Markdown
  body text in the same object.
- It does not pollute the repository's own issue tracker — records are stored
  as **draft issues** scoped to the Project, not as repository issues, so
  memory-record traffic does not show up as noise in `git log`-adjacent
  surfaces like the repo's Issues tab.
- It is reachable identically by both a Python/Actions-based transport and an
  Elixir/MCP-based transport, since both are just GraphQL clients against the
  same GitHub API surface — no shared runtime or shared code path is required
  for two independently-implemented agents to converge on the same store. See
  [two-transports-one-project.md](two-transports-one-project.md) for how those
  two transports actually stay in agreement.

## The read-before-manufacture / write-after-manufacture contract

Every one of the five named DfCM manufacturing cells — MEASURE, EXPLORE,
SELECT/DEVELOP, IMPLEMENT/QUALIFY, PORTFOLIO — is required to read, before
starting any work, in this order: `dfcm/frontier/current`, `dfcm/ledger/current`,
its own prior `latest` record, and the preceding cell's `latest` record (plus
any other memories it queries as relevant to its task). It is required to write
its own `latest` record after finishing, whether or not the run's actual
manufacturing work succeeded — even a no-op run gets recorded, because "nothing
happened this run" is itself information a future run needs in order not to
retry the same no-op blindly.

This ordering is not incidental. Skipping either the read or the write breaks
the mechanism's actual purpose: a cell that writes without reading risks
contradicting or duplicating what a concurrent or prior cell already recorded; a
cell that reads without writing leaves no trace for the next run to build on,
silently reverting the system to the "start from nothing" state this whole
mechanism exists to avoid. `project-memory/README.md`'s doctrine treats skipping
either half as making that run's memory-loop contract `BUILD_BROKEN` for that
run, independent of whether the underlying manufacturing work itself succeeded
— the memory discipline is graded separately from the work it accompanies.

## Immutability and the memory-key convention

Most keys are `latest`-style and get overwritten on each cell's run (e.g.
`dfcm/measure/latest`, `dfcm/portfolio/latest`) — they represent current state,
not history. A second, deliberately immutable category of key exists for
durable evidentiary or learning value specifically — for example
`dfcm/run/<cell>/<UTC-timestamp>/<head-sha>` — appended rather than overwritten,
so that a specific run's decisions remain inspectable even after `latest` has
moved on. The stated intent is that this immutable trail is for records with
lasting value, not a log entry per commit — the distinction is deliberate
curation, not exhaustive logging.

## The crown equation — stated precisely, including where the source is imprecise

The findings describe a set of named multipliers attached as `metadata` fields
on memory records: `E`, `E2`, `Y`, `R`, `C`, and a sixth slot. This sixth slot is
**not consistently named across the repo's own examples** — the request-schema
example in `project-memory/README.md` calls it `M`, while both
`project-memory/examples/dfcm-frontier-upsert.json` and the `dfcm/portfolio/latest`
row in the same README's own key table use `H5` for what appears to be the same
conceptual slot. This document deliberately does not resolve that inconsistency
by picking one name silently — the underlying source material itself disagrees,
and a reader relying on this document should know that rather than being handed
false certainty.

What each multiplier corresponds to at the *cell* level, per the memory-key
table:

| Key | Writer cell | Multiplier | Represents |
|---|---|---|---|
| `dfcm/measure/latest` | MEASURE | `E` | Latest observation set, sensors, measurement ERRC delta |
| `dfcm/explore/latest` | EXPLORE | `E2` | Non-dominated candidates, hypergraph delta |
| `dfcm/select/latest` | SELECT/DEVELOP | `Y` | Selected Pareto portfolio, capital allocation, preserved alternatives |
| `dfcm/implement/latest` | IMPLEMENT/QUALIFY | `R` | Canonical primitives, consumer census, qualification |
| `dfcm/portfolio/latest` | PORTFOLIO | `C` (and `H5`/`M`) | Autocatalytic generation state, next-cycle seeds |

Alongside these, the README states a cadence target: moving from a documented
50-commit-per-run floor toward `50 → 500 → 5,000 → 50,000` meaningful semantic
commits per run — explicitly framed, in the README's own words, as a
"search-expansion reference point, not a hard gate or padding quota." It is a
directional target for how much lawful, non-dominated work a run should be
capable of manufacturing as the memory loop accumulates value, not a literal
commit count any individual run is required to hit.

## What this document is not claiming

Nothing here asserts that the six-multiplier equation is a formally specified,
computed value anywhere in the codebase — the findings describe it as metadata
fields carried on records, populated by whatever process each cell uses to
assess its own contribution, not as a function implemented and evaluated by
code in this repo. Treat the multipliers as a shared *vocabulary* the cells use
to describe their contribution to the frontier, not as a proven formula this
repo computes and enforces.

## See also

- [two-transports-one-project.md](two-transports-one-project.md) — how the
  Python and Elixir/MCP transports onto this same Project stay in agreement
- [architecture-overview.md](architecture-overview.md) — where project-memory
  sits relative to the repo's other three subsystems
- [authority-model.md](authority-model.md) — the evidence/standing vocabulary
  (`ALIVE`/`BLOCKED`/`REFUSED_*`/etc.) that project-memory's own receipts use
