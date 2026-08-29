# chatgpt-cloud-elixir — ERRC Tracker

Standing ERRC (Eliminate/Reduce/Raise/Create) backlog for this repo, in the format
`~/.claude/skills/errc-cycle/SKILL.md` expects.

- **Open** — confirmed-real, not yet fixed. Ordered ELIMINATE → REDUCE → RAISE → CREATE.
- **Resolved** — fixed, one line each with a pointer to how/what proved it.
- **Misdiagnosed** — claims that turned out false on inspection; kept so nobody re-files them.
- **Parked** — genuinely ambiguous; needs a decision, not more auditing.

Three sweeps have fed this list: the original 2026-08-26 domain review (5 parallel
agents + an innovation-explorer pass); a 2026-08-29 reverify + 7-agent audit run
right after this branch merged ~28 independent feature/automation branches (2700+
commits) into one tree; and a second, larger 2026-08-29 pass (8 parallel agents
plus direct fixes) closing most of what the second sweep left Open. Every item
below reflects the latest 2026-08-29 state unless noted. **No Elixir/OTP toolchain
has been available in the environment any sweep ran in** — Elixir-only findings
are verified by reading/cross-referencing source (exhaustive grep, paren/bracket
balance, hand-traced control flow, sometimes a Python shadow implementation run
against constructed fixtures), not by `mix compile`/`mix test`; treat those as
`PARTIAL_ALIVE`, not `ALIVE`, until replayed in an environment with the toolchain.
Pure-Python/RDF fixes (rdflib/pyshacl are pip-installable in this sandbox and were
actually used) are real `ALIVE` results, not `PARTIAL_ALIVE` — noted per item.

## Critical

1. ~~**`mix ecto.migrate` fails on a fresh database.**~~ **FIXED, pending toolchain
   verification (2026-08-29).** Two migrations both `create table(:swarm_work_items,
   ...)` with incompatible column sets — the plain-Ecto
   `ChatGPTCloud.SwarmCoordination.WorkItem` schema
   (`20260826000000_create_swarm_coordination_tables.exs`, backs the raw HTTP
   SwarmSH JSON API) and the Ash resource
   `ChatGPTCloud.ProcessIntelligence.SwarmWorkItem`
   (`20260826173302_add_swarm_resources.exs`, generated via
   `mix ash_postgres.generate_migrations`, tested by
   `test/chatgpt_cloud/process_intelligence/swarm_test.exs`) — collided on the same
   table name during the branch merge; the second migration failed with Postgres
   `42P07` on any fresh database. Resolved by renaming the newer, Ash-generated
   side: `ChatGPTCloud.ProcessIntelligence.SwarmWorkItem`'s `postgres do table` is
   now `process_intelligence_swarm_work_items`, and
   `20260826173302_add_swarm_resources.exs` was hand-corrected to match (its own
   `@moduledoc` documents why this is a targeted correction of an
   already-broken-as-committed migration, not a routine hand-edit of a working
   one). The older plain-Ecto schema keeps `swarm_work_items` unchanged. Paren/bracket
   balance checked on both edited files; **still needs, in an environment with the
   toolchain**: `mix ash_postgres.generate_migrations` to confirm it reproduces (or
   no-ops against) this same rename, then `mix ecto.migrate` against a fresh
   database to confirm `42P07` no longer occurs. Treat as `PARTIAL_ALIVE`.
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
   language describes a gate that exists only on `main`/this branch. No workflow
   syncs `main` → `local-control-bus`, so nothing catches this drift automatically.
   **Underlying branch still not fixed here**: the remedy is pushing to a branch
   other than this session's designated one — a decision for whoever owns
   `local-control-bus`, not a unilateral fix. **Mitigated (2026-08-29)**: both
   installer scripts now refuse to proceed (`REFUSED[MISSING_APPROVAL_GATE]`,
   exit 4) if the cloned branch's `scripts/local_control_agent.py` lacks
   `class ApprovalStore`/`def requires_approval` — confirmed live against both this
   branch's agent (passes) and `local-control-bus`'s actual current content
   (correctly refuses). A fresh install today fails closed instead of silently
   running unguarded; the branch itself is still stale and still needs syncing.

## Open

### ELIMINATE

*(none currently open — the three items previously here are all in Resolved below)*

### REDUCE

- `scripts/` (24 files) flatly mixes three unrelated domains (capsule build/verify,
  manufacturing, project-memory) with no subdirectory grouping.
- `project-memory/` JSON formatting drifted (minified early → pretty-printed later)
  — pure `git diff`/grep noise across the corpus.
- `project-memory/` has no size discipline — growing by hundreds of files per day
  of active use, despite the README enforcing "don't explode into one card per
  commit" on the GitHub Project side but not on local transport files. (A pruning
  tool now exists — see Resolved's CREATE entry — but nothing runs it
  automatically yet; this item is about the lack of automatic discipline, not the
  lack of any tool at all.)
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
- (found 2026-08-29, while fixing the `AshAuthentication` false-ALIVE ELIMINATE
  item) Five independent modules under
  `control-plane/lib/chatgpt_cloud_control_plane/runtime_integration/` each
  maintain their own copy of "the admitted Ash extension list", never
  cross-checked against each other:
  `ChatGPTCloud.Ecosystem`/`ExtensionManifest`/`RuntimeManifest` (the group
  actually gating `ecosystem.ex`'s standing, just fixed to drop
  `:ash_authentication`) vs. `IgniterPlan`/`RuntimeExtensionWiring`/`RuntimeCapabilitySet`
  (a separate, self-contained "runtime integration plan" subsystem with its own
  tautological tests — each calls `.required()` to build its own input and verifies
  that input against itself). The second group still lists `:ash_authentication`;
  not touched by the fix above because doing so was outside that fix's scope and
  the second group isn't actually coupled to `ecosystem.ex` (no compile/runtime
  break either way — atoms don't require the backing package to exist), but it's
  now inconsistent with the first group and neither group would catch the other
  drifting.

### RAISE

- Test coverage cliff in `control-plane/`: dozens of lib files vs. a handful of real
  test files. Notably untested: `dfcm_memory/github_project_client.ex` (real
  external writes), `qualification.ex`/`qualification_reactor.ex` (state machine +
  Oban), `admin_auth.ex`/`ocel_auth.ex` (security-critical plugs), most Ash
  resources in `process_intelligence/resources.ex`.
- "Offline law" is only enforced via `scripts/run-offline.sh` /
  `scripts/run-postgres-offline.sh` — calling `verify-capsule.sh` or
  `verify-postgres-capsule.sh` *directly* still runs unfenced; nothing refuses the
  direct call. **Partially addressed 2026-08-29**: `verify-capsule.sh` no longer
  *lies* about it when called directly — its receipt's `network_mode` now defaults
  to an honest `unfenced_direct_call` sentinel (was `hex_offline`, indistinguishable
  from a real fenced run) and its `replay` field always points at
  `run-offline.sh`. The gap this item is actually about — nothing *prevents* the
  direct call — is unchanged.
- 8 of `ash-full` capsule's 15 required packages (AshPhoenix/Postgres/JsonApi/
  Authentication/Oban/GraphQL/AI/Money/Cloak/Archival/StateMachine) are verified
  only by `Code.ensure_loaded?`, not one real functional exercise — only
  `fixtures/ash_ets_smoke` exists as a real fixture. (Note: `Authentication` here
  is `AshPostgres`/other packages' own auth concerns, unrelated to the now-removed
  `ash_authentication` dep — see Resolved.)
- 180 of 1115 `project-memory/requests/*.json` (16%) have no matching receipt — 52
  of them mutating operations (48 `memory.upsert`, 1 `memory.create`,
  2 `memory.update`, 1 `memory.archive`) whose real effect on the live GitHub
  Project board is `UNKNOWN`, not `ALIVE` or `REFUSED`. Root cause, confirmed:
  `.github/workflows/project-memory-proxy.yml` computes its replay set from a
  combined `git diff-tree` over a merge commit's parents, and by design never
  replays a request file "inherited unchanged from a merged branch" even though
  the merge makes it newly present — exactly what this session's 28-branch merge
  did to any request whose branch-native CI run never landed a receipt. **A real,
  rerunnable detector now exists (2026-08-29)**: `scripts/project_memory_orphan_report.py`
  (read-only, `--json`/`--output` supported) reproduces these exact numbers on
  demand and additionally catches the 13 corrupted-JSON and 2 wrong-schema files
  below in one pass. Not yet wired into CI (the live corpus would fail the default
  threshold immediately — a human needs to pick a threshold/blocking policy first,
  see the tool's own `deferred_or_open` notes). The underlying 180 orphans
  themselves are still unresolved; still no dead-letter/alert mechanism beyond
  the new detector.
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

- `scripts/project_memory_proxy.py` supports `memory.query`/`memory.archive`/
  `memory.delete` but the MCP tool table only wraps
  `read`/`upsert`/`snapshot`/`list_project_items` — no `archive_dfcm_memory` /
  `delete_dfcm_memory` / `query_dfcm_memory` MCP tools exist. (2026-08-29: a related
  CREATE item, exposing `ConformanceResult`/`Refusal`/`ProcessVariant`/`SwarmTeam`
  as MCP tools, is now done — see Resolved — but that was on
  `ChatGPTCloud.ProcessIntelligence`'s domain; this item is `ChatGPTCloud.DfcmMemory`
  specifically and needs new backing GraphQL mutations against GitHub Project v2,
  not just router wiring — a materially bigger, network-logic-writing task that
  wasn't attempted blind without a way to test real GraphQL calls.)
- The vendored SwarmSH v2 checkout emits OTEL coordination events that never reach
  control-plane's OCEL ingest endpoint — the vendored coordination layer and the
  OCEL projection service don't talk to each other.

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
- `cc:CapabilitySource` ontology properties had zero domain/range/cardinality
  constraints (`manufacturing/ontology.ttl`). Added a real `sh:` SHACL shapes
  section (`cc:CapabilitySourceShape`, `@prefix sh: <http://www.w3.org/ns/shacl#>`)
  requiring exactly one each of `skos:prefLabel` (xsd:string), `dcterms:source`
  (`sh:nodeKind sh:IRI`), `cc:repository` (`sh:pattern` `"owner/repo"`-shaped),
  `cc:commitSha` (`sh:pattern` 40-hex), `cc:role`, `cc:capitalClass`,
  `cc:executionMode`, `cc:requiredStanding` (each `sh:nodeKind sh:Literal`).
  Added `scripts/verify-manufacturing-shacl.py`, a real rerunnable
  rdflib+pyshacl validator (shapes graph and data graph are the same file);
  actually run: `conforms=True` against all 7 real `cc:CapabilitySource`
  instances (ggen, ggen-marketplace, ggen-create, ggen-legacy, ggen-spec-kit,
  swarmsh, swarmsh-v2), and a negative test against a deliberately malformed
  instance confirmed the shapes genuinely reject (min/max-count and pattern
  violations fired, not a vacuous pass). Regression-checked:
  `manufacturing/queries/sources.rq` and `capability-lock.rq` still return 7
  rows each via rdflib against the edited file, and the existing
  regex-based `scripts/verify-autonomic-contract.py` still passes unchanged
  (`AUTONOMIC_CONTRACT=ALIVE`) — its `SOURCE_RE`/`SHA_RE` patterns don't
  overlap the new `sh:`-prefixed triples.
- `ggen/paas/` + `ggen/capability-lineage/` were confirmed-orphaned (no script,
  workflow, or doc anywhere referenced any filename or predicate from either
  tree) and, separately, it was unconfirmed whether `ggen/paas/runtime-admission/`'s
  claimed SHACL shapes were consumed by any validator/CI step at all. Not wired
  into a functional runtime-admission pipeline (a much larger, riskier
  undertaking, deliberately out of scope) — instead closed the achievable slice:
  added `scripts/verify-ggen-paas-shapes.py`, a real rerunnable rdflib+pyshacl
  validator, wired as a new, non-invasive job in
  `.github/workflows/ggen-paas-shapes-court.yml` (triggered on changes under
  either tree or the validator itself). Actually run against the real corpus
  (the directories hold 138 files total, not the 143 originally estimated —
  125 under `ggen/paas/` incl. 100 `runtime-admission/*.ttl`, 13 under
  `ggen/capability-lineage/`): all 112 `.ttl` files parse cleanly with rdflib
  (`format="turtle"`); rdflib triple-querying (not grep) independently confirms
  the set of files using `sh:NodeShape`/`sh:property` is *exactly* the 100
  `runtime-admission/*.ttl` files, no more, no fewer; all 100 load as SHACL
  shapes graphs with pyshacl and validate against a trivial data graph without
  erroring, both per-file and as one combined 1612-triple shapes graph (proves
  well-formed SHACL, not a functional check — there is no real runtime-admission
  data graph yet); all 26 `.rq` files parse as syntactically valid SPARQL via
  `rdflib.plugins.sparql.prepareQuery`. Negative-tested the validator itself
  (malformed Turtle and malformed SPARQL each correctly fail; pyshacl, as
  expected, does not hard-error on a malformed shape when there's no matching
  data to trigger the constraint — documented as a known limitation of "well-formed"
  vs. "functional" in the script's own docstring). Final: `GGEN_PAAS_SHAPES=ALIVE
  ttl=112/112 shacl=100/100 sparql=26/26`, exit 0.

**Fixed in a second, larger 2026-08-29 swarm pass** (8 parallel agents on the
remaining Open backlog, plus 4 fixes made directly):
- **Critical #1** (`swarm_work_items` migration collision) — see Critical section
  above for full detail; `PARTIAL_ALIVE`, needs toolchain replay.
- **Critical #2** (`local-control-bus` stale approval gate) — mitigated via a
  fail-closed installer check; see Critical section above. Underlying branch still
  needs a human to sync it.
- `scripts/verify-capsule.sh` and `capsules/process-intelligence/verify-capsule.sh`
  shared ~70% logic maintained as two copies (ELIMINATE/REDUCE). Extracted the
  genuinely-identical boilerplate into `scripts/lib/verify-capsule-common.sh`
  (`capsule_run_logged()` wrapper, manifest/runtime verification, standing
  computation, sha256/verified_at helpers); both entry scripts now source it and
  supply their own `verification_body()`. Everything that actually differs between
  the two capsules (network-mode default, release-version extraction, receipt
  field sets, the OCEL emission call) was deliberately left unmerged so external
  behavior is unchanged. `scripts/build-capsule.sh` updated to stage the new
  shared file. `bash -n` clean on all touched/new files; diffed against
  pre-refactor content to confirm zero behavior drift; a hand-written harness
  confirmed the extracted logging/status-capture wrapper's semantics match the
  original inline pattern exactly. Not run end-to-end (no toolchain) —
  `PARTIAL_ALIVE`.
- `capsules/process-intelligence/README.md` documented subject commit/tree SHAs
  that no longer matched `capsule.toml`'s actual pins. Corrected both SHA pairs
  (`ash_r2rml`, `ex4pm`) to match `capsule.toml` exactly; confirmed no other stale
  SHA references remained anywhere in the repo.
- `verifier/verify_manifest.exs` validated manifests via `String.contains?`
  substring search. Rewrote to use Elixir's built-in `JSON` module (stdlib since
  1.18.0, wrapping OTP 27's `:json` — confirmed available at both toolchains this
  script runs under: 1.20.2/OTP 29.0 and process-intelligence's separate
  1.18.4/OTP 27.2.4 pin) for real parsing, preserving the exact same required-key
  set, `versions.toml` regex check, stdout format, and exit codes (byte-for-byte
  diffed against the pre-edit version for the unchanged parts). Added two new
  `BUILD_BROKEN` branches (invalid JSON; non-object JSON) that couldn't exist
  under the old substring approach. Verified via a line-for-line Python shadow of
  the new control flow run against 5 constructed fixtures (all 5 produced the
  expected output/exit code) and a real fixture built by replaying
  `build-capsule.sh`'s own manifest-generation logic. Not run in Elixir itself
  (no toolchain) — `PARTIAL_ALIVE`.
- `ChatGPTCloud.Ecosystem.receipt/0` rolled `AshAuthentication`/
  `AshAuthentication.Phoenix` into its `ALIVE` gate via bare `Code.ensure_loaded?/1`
  with zero real usage anywhere in the app (confirmed by exhaustive grep before
  touching anything). Removed both from `ecosystem.ex`'s `@components`/
  `@runtime_extensions` and both deps from `mix.exs`. The initial pass surfaced a
  real coupling this closes too: `ChatGPTCloud.RuntimeIntegration.ExtensionManifest`
  (`@roles`) and `RuntimeManifest` (`@required_roles`) independently required the
  same `:operator_identity` role that only `ash_authentication` supplied — removing
  it from `ecosystem.ex` alone would have flipped `receipt/0`'s standing to
  `BUILD_BROKEN` via `RuntimeManifest.verify_roles/1` (traced by hand: `{:error,
  {:missing_runtime_roles, [:operator_identity]}}`), breaking the `precommit` alias
  and `ecosystem_test.exs`'s first test. Removed `:operator_identity`/
  `ash_authentication: :operator_identity` from both files, updated
  `ecosystem_test.exs`'s expected extension list, and removed `:ash_authentication`
  from `control-plane/.formatter.exs`'s `import_deps` (would otherwise error trying
  to import formatter config from a now-absent dep). `bcrypt_elixir` (flagged
  Parked, possibly transitive from `ash_authentication`) confirmed zero direct
  usage but deliberately left untouched — that's still a separate decision.
  `mix.lock` still carries `ash_authentication`/`ash_authentication_phoenix` and
  their likely-orphaned transitive deps — needs `mix deps.get`/`mix deps.clean` in
  a toolchain environment, not hand-edited. Paren/bracket balance checked on every
  edited file. Not compiled (no toolchain) — `PARTIAL_ALIVE`; the four files this
  fix touches (`ecosystem.ex`, `extension_manifest.ex`, `runtime_manifest.ex`,
  `ecosystem_test.exs`, `mix.exs`, `.formatter.exs`) need
  `cd control-plane && mix deps.get && mix compile --warnings-as-errors && mix test`
  before this can be called `ALIVE`.
- `ConformanceResult`/`Refusal`/`ProcessVariant` (live-populated by the ingestor)
  and `SwarmTeam` (real velocity/completed-work-item-count aggregates, already
  exercised by `swarm_test.exs`) had zero MCP/API exposure. Added
  `list_conformance_results`/`list_refusals`/`list_process_variants`/
  `list_swarm_teams` read-only AshAi tools to `process_intelligence/domain.ex`
  (mirroring the existing `list_qualifications` pattern exactly) and the matching
  4 atoms to `router.ex`'s `/mcp` tools list (16 → 20 total, existing 16
  untouched/unreordered). Deliberately did not add `json_api`/`graphql` exposure
  (would break `ecosystem_test.exs`'s exact-route/query-count assertions) or touch
  the separate Ash-native `SwarmWorkItem` resource (not what this item's file
  pointer asked for — still open, see CREATE above for the related still-open
  `SwarmWorkItem`/DfcmMemory MCP gaps). Updated `docs/reference/mcp-tools.md`'s
  tool table (4 new rows) and fixed its stale "exactly 6 tools" framing to the
  true 20. Verified all 4 new resources are registered in `domain.ex`'s
  `resources do` block and all 20 router atoms have exactly one matching `tool()`
  declaration; paren/bracket/do-end balance checked. Not compiled — `PARTIAL_ALIVE`.
- No pruning/archival/rotation policy existed for `project-memory/`. Added
  `scripts/project_memory_prune.py`: dry-run by default (reports candidates,
  makes zero writes), `--apply` moves (never deletes) requests+receipts for
  superseded "current"/"latest"-pointer keys into
  `project-memory/archive/<YYYY-MM>/`, always preserving each key's single most
  recent write. 30 tests, all passing; a real read-only dry-run against the live
  corpus reported 327 candidates across 27 pointer keys, matching the 13
  known-corrupted files exactly by name. `--apply` was never run against the real
  corpus in this pass (verified via `git status`/file-count/checksum diffing
  before and after) — this closes the "no tool exists" gap; actually running
  `--apply` against the live corpus is a separate, human-reviewed operational
  decision, not done here.

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
  now-removed `ash_authentication` deps (see Resolved above).
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
