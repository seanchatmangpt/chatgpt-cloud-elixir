# chatgpt-cloud-elixir — ERRC Tracker

Standing ERRC (Eliminate/Reduce/Raise/Create) backlog for this repo, in the format
`~/.claude/skills/errc-cycle/SKILL.md` expects.

- **Open** — confirmed-real, not yet fixed. Ordered ELIMINATE → REDUCE → RAISE → CREATE.
- **Resolved** — fixed, one line each with a pointer to how/what proved it.
- **Misdiagnosed** — claims that turned out false on inspection; kept so nobody re-files them.
- **Parked** — genuinely ambiguous; needs a decision, not more auditing.

Two sweeps have fed this list: the original 2026-08-26 domain review (5 parallel
agents + an innovation-explorer pass), and a 2026-08-29 reverify + second audit run
after this branch merged ~28 independent feature/automation branches (2700+
commits) into one tree. Every item below reflects the 2026-08-29 state unless noted.
**No Elixir/OTP toolchain has been available in the environment either sweep ran
in** — Elixir-only findings are verified by reading/cross-referencing source, not by
`mix compile`/`mix test`; treat those as `PARTIAL_ALIVE`, not `ALIVE`, until replayed
in an environment with the toolchain.

## Critical — fix before anything else here

1. **`mix ecto.migrate` fails on a fresh database.** Two migrations both
   `create table(:swarm_work_items, ...)` with incompatible column sets:
   `control-plane/priv/repo/migrations/20260826000000_create_swarm_coordination_tables.exs`
   (plain-Ecto schema `ChatGPTCloud.SwarmCoordination.WorkItem`, backs the raw HTTP
   SwarmSH JSON API) and `20260826173302_add_swarm_resources.exs` (Ash resource
   `ChatGPTCloud.ProcessIntelligence.SwarmWorkItem`, generated via
   `mix ash_postgres.generate_migrations`, tested by
   `test/chatgpt_cloud/process_intelligence/swarm_test.exs`). Both run in timestamp
   order against every fresh database; the second fails with Postgres `42P07`
   (relation already exists) — two independently-developed "swarm work" features
   collided on the same table name during the branch merge. **Needs a real decision**
   (which resource keeps `swarm_work_items`, what the other's table gets renamed to)
   plus a properly regenerated Ash migration (`mix ash_postgres.generate_migrations`
   — this repo's own convention is generated migrations are never hand-edited). Not
   safe to guess at without a compiler to verify against.
2. **`local-control-bus` branch is stale and missing the mandatory approval gate —
   a live security gap, not a doc lag.** `scripts/install-local-control-macos{,-user}.sh`
   clone the `local-control-bus` branch by default
   (`CHATGPT_LOCAL_CONTROL_BRANCH` env var overrides it), and launchd is configured
   to execute `scripts/local_control_agent.py` **from that branch's checkout**, not
   from `main`/this branch. `local-control-bus`'s last commit (2026-08-25 09:02)
   predates the entire mandatory-approval-gate feature added later the same day
   (22:12–22:17): no `ApprovalStore`, no `requires_approval`, no
   approve/deny/list-pending, no gating in `process_pending`.
   `local-control/AGENTS.md`'s "Requirement 9 ... deliberately unbypassable"
   language describes a gate that exists only on `main`/this branch. **Concretely:
   anyone who runs the installer today gets an agent that executes every admitted
   operation immediately with zero local human confirmation.** No workflow syncs
   `main` → `local-control-bus`, so nothing catches this drift automatically. Not
   fixed here: the remedy is pushing to a branch other than this session's
   designated one — a decision for whoever owns `local-control-bus`, not a
   unilateral fix.

## Open

### ELIMINATE

- `ChatGPTCloud.Ecosystem.receipt/0`
  (`control-plane/lib/chatgpt_cloud_control_plane/ecosystem.ex`) rolls
  `AshAuthentication`/`AshAuthentication.Phoenix` into its `standing: "ALIVE"` gate
  via bare `Code.ensure_loaded?/1`, with zero real `use`/DSL/router usage anywhere
  in the app outside this checker (real auth is hand-rolled Basic/bearer plugs,
  `ChatGPTCloudWeb.OcelAuth`) — false confidence, and the two deps are otherwise
  dead weight in `mix.exs`. Fixing needs an actual `mix test`/`mix dialyzer` run to
  confirm no regression from dropping them; left for an environment with the
  toolchain.
- `capsules/process-intelligence/verify-capsule.sh` is an 85-line copy-paste fork of
  `scripts/verify-capsule.sh` (72 lines), diverging only in the acceptance-loop
  body (see REDUCE below for the dedup version of this finding).
- "RDF/SHACL" framing is false *for `manufacturing/` specifically* — 8 files, no
  `sh:` constraints anywhere (`find manufacturing -iname "*shacl*"` → nothing).
  No longer true repo-wide: `ggen/paas/runtime-admission/*.ttl` (100 files, merged
  from `ws3/runtime-learning-shacl-20260827-20`) does use real SHACL vocabulary for
  Project2 runtime-admission guards — but see the orphaned-files item below; whether
  those shapes are consumed by any validator/CI step is unconfirmed.
- `ggen/paas/` + `ggen/capability-lineage/` (143 files: RDF contracts, numbered
  guards, ~100 of them SHACL-shaped runtime-admission shapes, plus SPARQL
  falsifier queries) are entirely orphaned — no script, workflow, or doc anywhere
  in the repo references any filename or predicate from either tree. Internally
  well-formed, but nothing executes them.
- `capsules/process-intelligence/README.md` documents subject commit/tree SHAs for
  `ash_r2rml`/`ex4pm` that no longer match `capsules/process-intelligence/capsule.toml`'s
  actual pins — pure doc drift (the build trusts `capsule.toml`, not the README),
  but misleads anyone checking "what exact commit is admitted" from the README.
  Likely a merge artifact from the 28-branch consolidation.

### REDUCE

- `scripts/` (18 files) flatly mixes three unrelated domains (capsule build/verify,
  manufacturing, project-memory) with no subdirectory grouping.
- `scripts/verify-capsule.sh` and `capsules/process-intelligence/verify-capsule.sh`
  share ~70% logic that should be one sourced helper, not two maintained copies.
- `cc:CapabilitySource` ontology properties (`manufacturing/ontology.ttl`) have zero
  domain/range/cardinality constraints — informal triples where SHACL would
  actually earn its keep (relates to the SHACL-framing item above).
- `ChatGPTCloud.Ecosystem.receipt/0` conflates three unrelated concerns (module-load
  check, state-machine shape, Oban schedule) in one untyped function.
- `project-memory/` JSON formatting drifted (minified early → pretty-printed later)
  — pure `git diff`/grep noise across the corpus.
- `project-memory/` has no size discipline — growing by hundreds of files per day
  of active use, despite the README enforcing "don't explode into one card per
  commit" on the GitHub Project side but not on local transport files.
- `docs/` is a near-1:1 doc-to-code ratio for the lib+capsule surface it covers;
  some reference pages (e.g. `docs/reference/r48-independent-consumer.md`, 9 lines)
  are thin single-topic footnotes.
- The SwarmSH checkout's `backlog.yaml` is upstream "Scrum at Scale" planning
  content, over a year stale, unrelated to this repo's actual work.
- `control-plane/lib/chatgpt_cloud_control_plane/runtime_contracts/` (107 lib + 54
  test files) uses namespace `ChatGPTCloudControlPlane.RuntimeContracts.*` while
  every other module in the app uses `ChatGPTCloud.*` — internally consistent and
  (as far as static reading can tell) compiles fine, but an unexplained
  two-convention split. A related residue:
  `test/chatgpt_cloud/runtime_integration/persistence_boundary_test.exs` passes
  `ChatGPTCloudControlPlane.Repo` (a module that doesn't exist — the real repo is
  `ChatGPTCloud.Repo`) as an inert placeholder, harmless since never invoked.
  Fixing the namespace split is a ~161-file mechanical rename — too large to do
  blind without a compiler to verify; left for an environment with the toolchain.

### RAISE

- Test coverage cliff in `control-plane/`: dozens of lib files vs. a handful of real
  test files. Notably untested: `dfcm_memory/github_project_client.ex` (real
  external writes), `qualification.ex`/`qualification_reactor.ex` (state machine +
  Oban), `admin_auth.ex`/`ocel_auth.ex` (security-critical plugs), most Ash
  resources in `process_intelligence/resources.ex`.
- "Offline law" is only enforced via `scripts/run-offline.sh` (and, since
  2026-08-29, `scripts/run-postgres-offline.sh`) — calling `verify-capsule.sh` or
  `verify-postgres-capsule.sh` *directly* still bypasses the network fencing while
  still stamping a receipt.
- `verifier/verify_manifest.exs` validates manifests via `String.contains?`
  substring search, not real JSON parsing/schema validation.
- 8 of `ash-full` capsule's 15 required packages (AshPhoenix/Postgres/JsonApi/
  Authentication/Oban/GraphQL/AI/Money/Cloak/Archival/StateMachine) are verified
  only by `Code.ensure_loaded?`, not one real functional exercise — only
  `fixtures/ash_ets_smoke` exists as a real fixture.
- 180 of 1115 `project-memory/requests/*.json` (16%) have no matching receipt — 52
  of them mutating operations (48 `memory.upsert`, 1 `memory.create`,
  2 `memory.update`, 1 `memory.archive`) whose real effect on the live GitHub
  Project board is `UNKNOWN`, not `ALIVE` or `REFUSED`. Root cause, confirmed:
  `.github/workflows/project-memory-proxy.yml` computes its replay set from a
  combined `git diff-tree` over a merge commit's parents, and by design never
  replays a request file "inherited unchanged from a merged branch" even though
  the merge makes it newly present — exactly what this session's 28-branch merge
  did to any request whose branch-native CI run never landed a receipt. (Separately,
  0 of 935 receipts are internally inconsistent, none are mislabeled `ALIVE` over a
  real failure, and 5 receipts have no matching request in the other direction.)
  Still no dead-letter/alert mechanism for either direction.
- 13 `project-memory/requests/*.json` files fail `json.loads` with the identical
  defect (exactly one extra trailing `}`) — a systematic corruption pattern, not 13
  independent typos. All 13 already have matching receipts that correctly recorded
  the failure (9 as `BUILD_BROKEN[UNHANDLED_PROXY_FAILURE]`, 4 — via the newer
  `project_memory_bus.py` front controller — as `REFUSED[INVALID_REQUEST_JSON]`),
  so no false success resulted, but the underlying writes never landed. Each writes
  to a "current"-pointer key that has since received dozens of later upserts, so
  resurrecting them now would very likely overwrite live state with stale data —
  left as historical provenance, not fixed, pending an explicit decision that a
  specific one should still land.
- 2 `project-memory/requests/*.json` files use an entirely different, envelope-less
  schema (`"type": "project2.work_claim"`, apparently for a separate work-claim/
  leasing mechanism) that `validate_request()` correctly and safely rejected
  (`REFUSED[INVALID_REQUEST]`) — no false success, but indicates two coordination
  mechanisms sharing one directory whose requests the CI push-trigger glob picks up
  indiscriminately.

### CREATE

- No pruning/archival/rotation policy anywhere for `project-memory/` — unbounded
  growth by construction at current cadence.
- `SwarmTeam`/`SwarmWorkItem` velocity aggregate
  (`control-plane/lib/chatgpt_cloud_control_plane/process_intelligence/swarm_team.ex`)
  has zero consumers — not in any LiveView, MCP tool, or `docs/reference/mcp-tools.md`.
- `scripts/project_memory_proxy.py` supports `memory.query`/`memory.archive`/
  `memory.delete` but the MCP tool table only wraps
  `read`/`upsert`/`snapshot`/`list_project_items` — no `archive_dfcm_memory` /
  `delete_dfcm_memory` / `query_dfcm_memory` MCP tools exist.
- The vendored SwarmSH v2 checkout emits OTEL coordination events that never reach
  control-plane's OCEL ingest endpoint — the vendored coordination layer and the
  OCEL projection service don't talk to each other.
- `ConformanceResult`/`Refusal`/`ProcessVariant` Ash resources are live-populated by
  the ingestor but not wired into `domain.ex`'s `tools`/`json_api`/`graphql`
  blocks — only `Qualification`/`CostObservation` get that exposure. Mirror the
  existing `list_qualifications` pattern
  (`control-plane/lib/chatgpt_cloud_control_plane/process_intelligence/resources.ex`,
  `domain.ex`).

## Resolved

Each fixed and verified against the merged tree as of 2026-08-29 (Elixir-only fixes:
structurally verified — cross-referenced against real backing code, paren/syntax
checked — not compiled; `mix compile && mix test` still needed before calling them
`ALIVE`). Grouped by when the fix landed.

**Already fixed by other branches merged into this one** (reverified, not
re-implemented):
- Dead script `scripts/manufacturing-sync-and-emit.sh` — deleted, zero references
  confirmed beforehand.
- `mix.exs` `precommit` alias — now runs `format --check-formatted`,
  `compile --warnings-as-errors`, `chatgpt_cloud.ecosystem.verify`, `test --cover`,
  `dialyzer`.
- `docs/reference/mcp-tools.md` — carries a `> **Security:**` callout naming
  `OCEL_INGEST_TOKEN` as the single credential gating OCEL ingestion, the MCP tool
  set (incl. `upsert_dfcm_memory`), `/graphql`, and `/api/json`.
- `scripts/project_memory_proxy.py` — `main()` has a dedicated
  `except json.JSONDecodeError` branch (`reason: "MALFORMED_REQUEST_JSON"`, with
  line/column/char detail), distinct from the generic `UNHANDLED_PROXY_FAILURE`
  branch. The 9 pre-existing `BUILD_BROKEN` receipts from before this fix landed
  are left as historical provenance, not retroactively rewritten.
- 6 scripts were missing `+x` while every caller invoked them via `bash script.sh`
  explicitly (so never functionally load-bearing) — `chmod +x`'d for consistency:
  `scripts/{build,verify}-autonomic-manufacturing.sh`,
  `scripts/{install,uninstall}-local-control-macos{,-user}.sh`.

**Fixed in this session's own 2026-08-29 audit pass:**
- Capsule builds silently dropped `scripts/emit-ocel-capsule-event.sh` from 6 of 8
  capsule kinds' staged `scripts/`, permanently (but silently, via `|| true`)
  disabling OCEL observability emission on every build. Fixed in
  `scripts/build-capsule.sh` and `scripts/build-autonomic-manufacturing.sh`.
- `capsules/ash-postgres` and `ash-phoenix` `capsule.toml` listed
  `spark`/`reactor`/`igniter` in `packages` but omitted the matching
  `Spark`/`Reactor`/`Igniter` from `required_modules` — their generated
  `CapsuleModulesTest` acceptance check never actually asserted those three
  modules loaded. Fixed both; added `scripts/verify-capsule-package-consistency.py`
  (wired into `.github/workflows/build-capsules.yml` as a gating job) to catch this
  class of drift mechanically going forward.
- `control-plane/config/dev.exs` was missing `browser_auth_required: false` — any
  browser route in `mix phx.server` dev mode (the README's own documented
  workflow) crashed with `ArgumentError` from `AdminAuth`'s `Application.fetch_env!`.
- The `/mcp` router only forwarded 4 of 16 declared AshAi tools, contradicting
  `README.md`'s documented "Project Two semantic PaaS"/"Vision 2030" MCP surface —
  all 16 have real backing actions; added the missing 10.
- `manufacturing/ontology.ttl`'s capsule-level triples (`releaseVersion`,
  `authorityCeiling`) were asserted but never queried, so
  `capability-lock.json.tera` hardcoded them as literals instead of deriving them.
  Added `manufacturing/queries/capability-lock.rq` and wired it in; hand-traced the
  new binding against the ontology to confirm output is unchanged.
- `local-control/receipt.schema.json` allowed an unused `PENDING_APPROVAL` standing
  no code path ever emits (removed); two `Refused` exception paths in
  `scripts/local_control_agent.py` weren't recorded in the local replay ledger, so
  the README's "deleting a receipt cannot silently authorize replay" invariant
  didn't literally hold for those two paths (fixed).
- `.github/workflows/ggen-ecosystem-ocel-consumer.yml`'s push trigger was scoped to
  a now-merged feature-branch name rather than `main`.
- `scripts/verify-postgres-capsule.sh` had no `run-offline.sh`-equivalent
  network-fenced entry point (every Elixir capsule kind had one) — added
  `scripts/run-postgres-offline.sh`, wired into `build-postgres-capsule.sh` staging.
- No cross-validation that `capsules/*/capsule.toml` package sets stay consistent
  with each other or `versions.toml` — see the ash-postgres/ash-phoenix fix above;
  same script closes both.
- `control-plane/deps` and `control-plane/_build` (~5,800 files / 1.37M lines) had
  been accidentally committed during the branch merge — removed from tracking,
  added `control-plane/.gitignore` (root `.gitignore`'s `/_build`/`/deps` are
  root-anchored and never covered this nested app); the two real submodules
  (daisyui, heroicons) were preserved.
- `CLAUDE.md`/`README.md`/`AGENTS.md` layout sections hadn't caught up to this
  session's merge (missing `ggen/`, `ontology/`+`templates/`+`ggen.toml`,
  `local-control/`, `verification/`, `tests/`, `.capability-sources/`; stale
  workflow/capsule counts) — updated to match the current tree.
- No `docs/reference/vendors.md` — added, documenting the external-checkout
  contract for `manufacturing/`'s dependencies. Mid-write, found the directory
  those checkouts actually land in is `.capability-sources/`
  (`scripts/build-autonomic-manufacturing.sh`'s `CAPABILITY_SOURCE_ROOT`), not
  `vendors/` — root `.gitignore`'s `vendors/` entry is currently vestigial,
  referenced by no script or workflow. Documented under the accurate name.

## Misdiagnosed

- **"`scripts/verify-autonomic-manufacturing.sh` checks the wrong vendor path
  (`$ROOT/swarmsh/` instead of `vendors/swarmsh/`)."** Not reproduced.
  `$ROOT` in that script is the *installed capsule's* root at consume-time, not this
  repo — `scripts/build-autonomic-manufacturing.sh` stages the SwarmSH source at
  `$STAGE/swarmsh` (which becomes the capsule's `$ROOT/swarmsh`), matching the
  verify script exactly. A checkout at `vendors/swarmsh/` (or `.capability-sources/swarmsh/`
  — see `docs/reference/vendors.md`) is a different, build-time-only, repo-side
  location that correctly does not exist inside a shipped, relocatable capsule. The
  two scripts are internally consistent with each other. (End-to-end pass/fail is
  still unverified — no `ggen` binary or vendored SwarmSH source has been available
  in either sweep's sandbox to actually run the build.)
- **"`vendors/swarmsh` and `vendors/swarmsh-v2` are unpinned — no commit SHA/tag/
  lockfile."** False. `manufacturing/ontology.ttl` declares exact pinned SHAs for
  both (`745008438b9493d31e8af3735ad6116ac01c150f`,
  `02e5eaae14bd03a832c0f031acc56c6d4db3845e`), restated in
  `manufacturing/generated/capability-lock.json`. Narrower residual, not part of
  the original claim: neither checkout was confirmed detached-HEAD in the one
  sweep that had a live checkout on disk, so a stray `git pull` could still drift
  silently with no automated check.

## Parked (genuinely ambiguous — needs a decision, not more investigation)

- `manufacturing/.ggen/keys/` and `.ggen-v2/receipt-log.jsonl` — untracked; unclear
  if intentionally ephemeral or should be gitignored explicitly.
- `SecretCredential` resource omits the JSON:API/GraphQL extension — looks
  correct-by-design (secrets shouldn't be API-exposed) but unconfirmed.
- `bcrypt_elixir` dep — no direct usage found; possibly transitive from the unused
  `ash_authentication` deps (see ELIMINATE above).
- `capsules/process-intelligence/capsule.toml` pins a different OTP/Elixir runtime
  than root `versions.toml` — may be intentional (pins external subject repos' own
  toolchain) but undocumented.
- `docs/reference/r48-independent-consumer.md` cites external `ggen-marketplace`
  SHAs unverifiable from this repo alone.
- `project-memory/` README's documented standings (`ALIVE/REFUSED/BLOCKED/UNKNOWN/
  BUILD_BROKEN`) don't match what's on disk (`PARTIAL_ALIVE`, `RUNNING`, `COMPLETE`,
  `REQUALIFYING` all appear) — doc vs. reality drift, unclear which is authoritative.
- The SwarmSH checkout's CHANGELOGs look like genuine upstream release notes —
  plausible but unconfirmable without upstream HEAD access.

## See Also

- `docs/errc-8020-vital-few.md` — the original 80/20 "vital few" cut of this
  backlog; all four of its items are now in Resolved above, kept for citation
  history (`docs/reference/vendors.md` and `scripts/verify-capsule-package-consistency.py`
  reference its §3).
- `~/.claude/skills/errc-cycle/SKILL.md` — the process this tracker feeds.
