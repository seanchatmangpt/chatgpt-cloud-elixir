# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

`chatgpt-cloud-elixir` manufactures **portable, offline-capable Erlang/Elixir/Ash runtime
capsules** for restricted ChatGPT cloud containers that can execute Linux binaries but
cannot reliably reach Hex/apt/DNS. GitHub Actions builds and transports capsules; it is
never the test oracle. The only crown is: exact admitted capsule + exact acceptance
command executed locally in the consuming environment.

Read `AGENTS.md` and `README.md` before making changes — they are the canonical operating
contract (evidence vocabulary, offline law, capsule lifecycle) and are more authoritative
than this file for *how* to work here.

## Status vocabulary (used everywhere: commits, PRs, receipts)

`UNKNOWN | PARTIAL_ALIVE | ALIVE | BLOCKED | BUILD_BROKEN | UNSUPPORTED` (+ typed
`REFUSED_*`). `ALIVE` means the exact admitted subject executed the exact acceptance
command — not "workflow exists," "artifact uploaded," or "a file named receipt.json is
present." Never claim `ALIVE` without that replay evidence.

## Repository layout (multiple independent manufacturing surfaces)

```
capsules/<name>/capsule.toml   — capsule contracts (requirements + acceptance commands)
scripts/                       — build-*.sh / verify-*.sh / install-capsule.sh / run-offline.sh
verifier/                      — verify_manifest.exs, verify_runtime.exs (Elixir-side checks)
fixtures/                      — mix_smoke/, ash_ets_smoke/ real acceptance fixtures
versions.toml                  — canonical version-selection surface (OTP/Elixir/Ash/... pins)

manufacturing/                 — ggen-driven RDF→capability-lock pipeline (see below)
control-plane/                 — Phoenix/Ash app: persistent OCEL projection service (Fly-deployed)
project-memory/                — GitHub Project v2 used as a bounded persistent memory proxy
.capability-sources/           — .gitignore'd, exact-SHA-pinned external checkouts
                                  (SwarmSH, the ggen* ecosystem) that manufacturing/
                                  and capsules/autonomic-manufacturing/ depend on
                                  (scripts/build-autonomic-manufacturing.sh's
                                  CAPABILITY_SOURCE_ROOT); root .gitignore also still
                                  lists a `vendors/` entry that nothing currently
                                  reads/writes — see docs/reference/vendors.md.
ggen/                          — SHACL-shaped runtime-admission + capability-lineage
                                  RDF guards (ggen/paas/, ggen/paas/runtime-admission/
                                  [100 files], ggen/capability-lineage/); distinct from
                                  manufacturing/'s ggen pipeline; not currently invoked
                                  by any workflow or script.
ontology/, templates/, ggen.toml — a second, separate ggen pipeline ("GGEN Ecosystem
                                  OCEL"): projects GitHub Project #2's current
                                  manufacturing state via
                                  .github/workflows/ggen-ecosystem-ocel-consumer.yml
                                  and project-memory/GGEN-ECOSYSTEM-OCEL.md — do not
                                  confuse with manufacturing/ontology.ttl, a different
                                  ontology for the autonomic-manufacturing capsule.
local-control/                 — bounded local-actuation transport (own AGENTS.md,
                                  README.md): GitHub-mediated request/receipt bus
                                  (local-control-bus branch) to a user-run local agent
                                  (scripts/local_control_agent.py).
verification/                  — r48-independent-consumer fixture
                                  (verification/r48-consumer/consumer.json), backing
                                  .github/workflows/r48-independent-consumer.yml.
tests/                         — top-level Python pytest suite spanning
                                  project-memory, local-control, OCEL emission, and
                                  semantic projection (not just project-memory/).
docs/                           — Diátaxis-structured documentation tree; see
                                  docs/README.md, the current fullest map of this repo.
.github/workflows/               — 18 workflow files (as of this writing) covering capsule
                                  build/verify, control-plane CI/format/deploy, the two
                                  ggen pipelines (autonomic-manufacturing + GGEN Ecosystem
                                  OCEL), local-control CI, project-memory proxy, release
                                  integrity, and several standing court/qualification
                                  checks — no longer one-per-surface.
```

Generated capsule archives, manifests, checksums, receipts, and `manufacturing/generated/*`
are **build projections** — never hand-edit them. Edit the owning source (`versions.toml`,
`capsule.toml`, `ontology.ttl`, script) and regenerate.

### Capsule graph (`capsules/`)

- `beam-core` — Erlang/OTP, Elixir, Mix, Hex, Rebar3.
- `ash-core` — beam-core + Ash/Spark/Reactor + a real ETS-backed Ash acceptance app.
- `ash-postgres`, `ash-phoenix`, `ash-full` — incremental Ash ecosystem closures.
- `postgres17` — standalone PostgreSQL 17 service capsule.
- `process-intelligence` — capsule backing the `control-plane` app's offline crown.
- `autonomic-manufacturing` — the ggen + SwarmSH ecosystem closure capsule (see
  `manufacturing/`).

Each capsule's contract lives in its `capsule.toml`; version pins come from
`versions.toml` (schema documents `[bootstrap]`, `[runtime]`, `[packages]`, `[services]`,
`[platforms]`, `[standing]`).

### `manufacturing/` — ggen-driven capability closure

RDF ontology (`ontology.ttl`) is the authoritative source of the external capability-source
set (ggen, ggen-marketplace, ggen-create, ggen-legacy, ggen-spec-kit, swarmsh, swarmsh-v2).
`versions.toml`'s `[bootstrap]` holds only the minimal ggen trust anchor needed to build the
compiler; `manufacturing/queries/*.rq` + `manufacturing/templates/*.tera` project the full
`capability-lock.json` and topology diagram via `ggen sync run`. Pipeline:

```
ontology.ttl → pinned ggen bootstrap → ggen sync run → capability-lock.json + topology
  → fetch exact ecosystem SHAs → autonomic-manufacturing capsule → fresh-consumer replay → receipt
```

`scripts/verify-autonomic-contract.py` mechanically enforces that the bootstrap ggen SHA in
`versions.toml` matches the ggen identity admitted in the ontology. This surface is
`CONSTRUCT_VERIFY` only — it does not grant ambient external `DO` authority (see
`manufacturing/README.md`).

### `control-plane/` — Phoenix/Ash operational projection

A separate, standing Phoenix/Ash app (`chatgpt_cloud_control_plane`, Elixir `~> 1.20`,
`compilers: [:phoenix_live_view]`) that continuously observes/projects admitted OCEL events
from agents/CI/producers. It does **not** replace the offline capsule crown — it is a live
service, deployed to Fly (`fly.toml`, `scripts/bootstrap-fly.sh`,
`.github/workflows/deploy-fly.yml`, credential-gated on `FLY_API_TOKEN`).

Key surfaces: `/process-intelligence/live` (LiveView OCEL feed), `/mcp` (AshAi MCP tool
server — see docs/reference/mcp-tools.md), `/admin` (AshAdmin), `/api/v1/ocel/batches`
(bearer-token OCEL ingest), `/healthz`.

### `project-memory/` — GitHub Project v2 as memory

Turns GitHub Project `seanchatmangpt/2` into bounded persistent memory. Flow: write a
request JSON to `project-memory/requests/<id>.json` → push-triggered Action runs
`scripts/project_memory_bus.py` (fail-closed front controller) → dispatches mutating
operations to `scripts/project_memory_proxy.py` and read-only semantic/graph/Vision-2030
projections to `scripts/project_memory_semantic_proxy.py` → authenticated GraphQL mutation
→ receipt written to `project-memory/receipts/<id>.receipt.json`. Hard-scoped to owner
`seanchatmangpt`, project `2`; raw GraphQL is rejected. Base operations: `project.snapshot`,
`project.items`, `memory.create`, `memory.read`, `memory.update`, `memory.upsert`,
`memory.query`, `memory.archive`, `memory.delete`. Semantic/read-only operations (see
docs/reference/project-memory-protocol.md for the full list): `project.semantic`,
`project.graph`, `project.graph.query`, `project.tables`, `project.triples`,
`project.jsonld`, `project.services`, `project.ocel`, `project.context`,
`project.vision2030`. Missing/unauthorized `PROJECTS_TOKEN` → receipt records
`BLOCKED[IRREDUCIBLE_AUTHORITY]`, never a faked success.

## Commands

### Capsule build/verify (root)

```bash
scripts/build-capsule.sh <capsule-name>            # manufacture a capsule archive
scripts/inspect-capsule.sh <capsule-path>           # inspect without extracting
scripts/install-capsule.sh <capsule-path> <dest>    # extract + activate, relocatable
scripts/verify-capsule.sh <capsule-path>            # clean-consumer verification
scripts/run-offline.sh ...                          # run a command inside the offline capsule
scripts/build-postgres-capsule.sh / verify-postgres-capsule.sh / run-postgres-offline.sh
scripts/build-autonomic-manufacturing.sh / verify-autonomic-manufacturing.sh
scripts/build-process-intelligence.sh
scripts/verify-autonomic-contract.py                # ontology<->bootstrap identity check
scripts/verify-capsule-package-consistency.py       # capsule.toml <-> versions.toml cross-check
scripts/verify-release.py
```

Ash fixture acceptance (what a capsule must be able to run):

```bash
MIX_ENV=test mix compile --warnings-as-errors && mix test
```

Elixir-side verifier scripts: `elixir verifier/verify_manifest.exs`,
`elixir verifier/verify_runtime.exs`.

### `manufacturing/` (ggen)

```bash
cd manufacturing && ggen sync run     # projects generated/capability-lock.json + .mmd topology
```

### `control-plane/` (Phoenix/Ash)

```bash
cd control-plane
mix setup                                              # deps + db setup
OCEL_INGEST_TOKEN=dev-ocel-token mix phx.server         # run locally
mix test                                                # run test suite
mix test path/to/file_test.exs:LINE                     # single test
mix precommit                                           # preferred_envs: precommit -> :test
```

### `project-memory/` (Python proxy + tests)

```bash
python3 -m pytest tests/test_project_memory_proxy.py
python3 -m py_compile scripts/project_memory_proxy.py
```

## Working conventions

- Purpose branch → intentional commit → non-force push → draft PR → **no merge** unless
  explicitly requested (`AGENTS.md`, "GitHub / receipt").
- Never rerun an unchanged failed network/Hex/DNS/`apt` operation without a new hypothesis
  (offline law) — an admitted offline capsule that unexpectedly fetches from Hex is
  `BUILD_BROKEN`.
- Capsules must never contain GitHub tokens, Hex publishing credentials, CI secrets, cloud
  credentials, or runner identity material.
- End substantive work with a receipt binding: target/self repo+SHA, capsule
  name/version/digest, observed environment, commands+exit codes, tests/results, final
  standing, replay command, branch/PR — not a narrated summary.
