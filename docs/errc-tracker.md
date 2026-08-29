# chatgpt-cloud-elixir — ERRC Tracker

Standing ERRC (Eliminate/Reduce/Raise/Create) backlog for this repo, in the format
`~/.claude/skills/errc-cycle/SKILL.md` expects. Seeded 2026-08-26 from two prior
sweeps run this session:

- A 5-agent parallel domain review (capsule manufacturing core, control-plane/,
  manufacturing/ ggen pipeline, project-memory/, docs+governance+vendors) — the
  primary source of the items below.
- An `innovation-explorer` cycle (`docs/innovation-exploration-v26.9.1-cycle-report.md`)
  whose top "unexploited-capability" candidates are folded into CREATE below.

All items are **open** — none have been through an errc-cycle Verify pass yet.

> **2026-08-29 reverify note:** this branch (`claude/zoela-ultracode-merge-finish-8ye7ov`)
> merges ~28 independent feature/automation branches, several created *after* this
> tracker's 2026-08-26 seed date. A spot-reverify of every item below against the
> merged tree found items 3, 19, 24, 25 already resolved by those later branches
> (struck through in place, with evidence) and item 9 misdiagnosed (also struck
> through, with evidence) — see also `docs/errc-8020-vital-few.md` §0/§3. Items not
> annotated below were not re-verified in this pass and should not be assumed either
> still-open or resolved without checking. No Elixir/OTP toolchain was available in
> the environment this reverify ran in, so any item requiring `mix compile`/`mix test`
> to confirm stays UNKNOWN rather than claimed ALIVE or resolved.

## Backlog (Cycle 0 — initial seed, unverified)

### ELIMINATE

1. "RDF/SHACL" framing is false — no SHACL shapes exist anywhere in `manufacturing/`.
   Evidence: `find manufacturing -iname "*shacl*"` → nothing; `ontology.ttl` has no
   `sh:` constraints. **Partially stale (reverified 2026-08-29)**: still true for
   `manufacturing/` specifically (unchanged, 8 files, no SHACL). No longer true
   repo-wide: `ggen/paas/runtime-admission/*.ttl` (100 files, merged from
   `ws3/runtime-learning-shacl-20260827-20`, one day after this tracker was seeded)
   does use real `sh:` SHACL vocabulary for Project2 runtime admission guards. Whether
   those 100 shapes are actually consumed by a validator/CI step was not checked in
   this pass.
2. `capsules/process-intelligence/verify-capsule.sh` is an 85-line copy-paste fork of
   `scripts/verify-capsule.sh` (72 lines), diverging only in the acceptance-loop body.
3. ~~`scripts/manufacturing-sync-and-emit.sh` — dead script, zero external
   references (not called by any workflow, doc, or other script).~~ **RESOLVED
   2026-08-26**: deleted (`git rm scripts/manufacturing-sync-and-emit.sh`),
   confirmed zero references remained before removal.
4. `ChatGPTCloud.Ecosystem.receipt/0` (`control-plane/lib/chatgpt_cloud_control_plane/ecosystem.ex:33-38`)
   only checks `Code.ensure_loaded?/1` per dependency — reports `AshAuthentication`
   as "ALIVE" despite zero real usage. Gives false confidence.
5. `ash_authentication` / `ash_authentication_phoenix` deps (pre-release versions,
   `mix.exs`) are dead weight — grep confirms zero `use`/DSL/router usage outside the
   fake `ecosystem.ex` checker. Real auth is hand-rolled Basic/bearer plugs.
6. 43/342 (~12.5%) of `project-memory/requests/*.json` have no matching receipt, with
   no dead-letter or alert mechanism. Example:
   `project-memory/requests/20260825T092300Z-measure-snapshot-pre.json`.
   **Still open, reverified 2026-08-29** (numbers updated, not resolved): corpus has
   grown to 1104 requests / 935 receipts; 174 requests (15.8%) now have no matching
   receipt — the underlying rate is roughly stable-to-worse, not improving as the
   corpus grows. Still no dead-letter/alert mechanism found. (5 receipts also have no
   matching request — orphans in the other direction, not previously noted.)
7. `vendors/swarmsh` — ~264 files of dead weight (telemetry dumps, `.backup.*` copies
   of `coordination_helper.sh`, speculative arxiv-paper drafts). Only 2 files
   (`coordination_helper.sh`, `real_agent_coordinator.sh`) are actually load-bearing.
8. `vendors/swarmsh{,-v2}` are unpinned — no commit SHA/tag/lockfile, despite
   `AGENTS.md` mandating exact-SHA pinning for anything used by/against this repo.
9. ~~`scripts/verify-autonomic-manufacturing.sh` checks the wrong vendor path
   (`$ROOT/swarmsh/` instead of the real `vendors/swarmsh/`) — confirmed BUILD_BROKEN
   by the repo's own evidence vocabulary; no top-level `swarmsh/` dir exists.~~
   **MISDIAGNOSED, reverified 2026-08-29**: `$ROOT` here is the *installed capsule's*
   root at consume-time, not this repo — `scripts/build-autonomic-manufacturing.sh`
   stages SwarmSH source at `$STAGE/swarmsh` (which becomes the capsule's `$ROOT/swarmsh`),
   matching the verify script exactly. `vendors/swarmsh/` is a separate, repo-side,
   build-time-only source location, correctly absent from the shipped capsule. See
   `docs/errc-8020-vital-few.md` §3 item 9 for full evidence. Not a bug as stated;
   end-to-end build/verify still UNKNOWN (no `ggen` binary or vendored SwarmSH source
   available to actually run it in the environment this reverify ran in).

### REDUCE

10. `scripts/` (17 files) flatly mixes 3 unrelated domains (capsule build/verify,
    manufacturing, and a 28KB `project_memory_proxy.py`) with no subdirectory
    grouping.
11. `scripts/verify-capsule.sh` and `capsules/process-intelligence/verify-capsule.sh`
    share ~70% logic that should be one sourced helper, not two maintained copies
    (see also ELIMINATE #2).
12. `cc:CapabilitySource` ontology properties (`manufacturing/ontology.ttl:64-72`) have
    zero domain/range/cardinality constraints — informal triples where SHACL would
    actually earn its keep (relates to ELIMINATE #1's false-framing finding).
13. `ChatGPTCloud.Ecosystem.receipt/0` conflates 3 unrelated concerns (module-load
    check, state-machine shape, Oban schedule) in one untyped function.
14. `project-memory/` JSON formatting drifted (minified early → pretty-printed later)
    — pure `git diff`/grep noise across the corpus.
15. `project-memory/` is growing ~840 files / 9.2MB **per day** with no size
    discipline, despite the README enforcing "don't explode into one card per commit"
    on the GitHub Project side but not on local transport files.
16. `docs/` — 30 files / 2,840 lines for a 41-file lib+capsule surface (~1:1
    doc-to-code ratio); `docs/reference/r48-independent-consumer.md` (9 lines) and
    `docs/reference/mcp-tools.md` (38 lines) are thin single-topic footnotes.
17. `vendors/swarmsh/backlog.yaml` — over a year stale (`last_updated: 2025-06-15`),
    unrelated "Scrum at Scale" planning cruft with no connection to this repo's work.

### RAISE

18. Test coverage cliff in `control-plane/`: 32 lib files vs. 4 real test files.
    Untested: `dfcm_memory/github_project_client.ex` (574 lines, real external
    writes), `qualification.ex`/`qualification_reactor.ex` (state machine + Oban),
    `admin_auth.ex`/`ocel_auth.ex` (security-critical plugs), all 10+ Ash resources
    in `process_intelligence/resources.ex`.
19. ~~`mix.exs` `precommit` alias has no `mix test --cover` or `mix dialyzer` — the
    coverage gap in #18 is invisible to CI.~~ **RESOLVED (reverified 2026-08-29)**:
    `control-plane/mix.exs` `precommit` alias now runs `format --check-formatted`,
    `compile --warnings-as-errors`, `chatgpt_cloud.ecosystem.verify`, `test --cover`,
    `dialyzer`. Confirmed by reading `mix.exs` directly; actual pass/fail of the suite
    is UNKNOWN — no Elixir/OTP toolchain available in the sandbox this reverify ran in.
20. "Offline law" is only enforced via `scripts/run-offline.sh`; calling
    `verify-capsule.sh` directly can silently fetch from Hex while still stamping
    `receipt.json` with `hex_offline`. ~~`verify-postgres-capsule.sh` has no
    offline-fenced entry point at all.~~ **PARTIALLY RESOLVED (2026-08-29)**: added
    `scripts/run-postgres-offline.sh`, mirroring `run-offline.sh`'s network-fencing
    contract (prefers `unshare -n`, falls back to a dead loopback proxy) for
    `verify-postgres-capsule.sh`, and wired it into `build-postgres-capsule.sh`'s
    staging step so it ships inside the postgres17 capsule. `bash -n` clean on both
    changed scripts; not run end-to-end (no built postgres capsule available in the
    sandbox this fix was made in). The `verify-capsule.sh`-can-be-called-directly
    half of this item is unchanged/still open.
21. `verifier/verify_manifest.exs` validates manifests via `String.contains?`
    substring search, not real JSON schema validation (`verifier/verify_manifest.exs:5-14`).
22. 8 of `ash-full` capsule's 15 required packages (AshPhoenix/Postgres/JsonApi/
    Authentication/Oban/GraphQL/AI/Money/Cloak/Archival/StateMachine) are verified
    only by `Code.ensure_loaded?`, not one real functional exercise — only
    `fixtures/ash_ets_smoke` exists as a real fixture.
23. `manufacturing/ontology.ttl` models `cc:ManufacturingCapsule`,
    `cc:AutonomicManufacturingCapsule`, `cc:CONSTRUCT_VERIFY` but only 1 of 3 classes
    (`CapabilitySource`) is ever queried by `manufacturing/queries/sources.rq`.
24. ~~`docs/reference/mcp-tools.md` documents the single bearer token gating
    OCEL/DfCM/GraphQL/JSON:API — the most security-load-bearing doc in the repo,
    filed as a plain "reference" page with no security callout.~~ **RESOLVED
    (reverified 2026-08-29)**: `docs/reference/mcp-tools.md` lines 30-34 carry a
    `> **Security:**` callout naming exactly this (`OCEL_INGEST_TOKEN` gates OCEL
    ingestion, the MCP tool set incl. `upsert_dfcm_memory`, `/graphql`, `/api/json`).
25. ~~9 `project-memory/` receipts are `BUILD_BROKEN` from unhandled JSON parse
    exceptions in `scripts/project_memory_proxy.py` — no defensive shape validation,
    recurred repeatedly same day with no fix landing.~~ **RESOLVED (reverified
    2026-08-29)**: `main()` in `scripts/project_memory_proxy.py` now has a dedicated
    `except json.JSONDecodeError as exc:` branch (`reason: "MALFORMED_REQUEST_JSON"`,
    with line/column/char in `error.details`), distinct from the generic
    `except Exception` (`UNHANDLED_PROXY_FAILURE`) branch. `python3 -m pytest tests/`
    passes (57 passed, 9 subtests) covering this module. The 9 pre-existing
    `BUILD_BROKEN[UNHANDLED_PROXY_FAILURE]` receipts predate the fix and are left as
    historical provenance, not retroactively rewritten.

### CREATE

26. `manufacturing/templates/capability-lock.json.tera` hardcodes
    `"release": "26.8.25"` / `"authority_ceiling": "CONSTRUCT_VERIFY"` as template
    literals instead of deriving them from the ontology's own
    `cc:releaseVersion`/`cc:authorityCeiling` triples.
27. No pruning/archival/rotation policy anywhere for `project-memory/` — unbounded
    growth by construction at current cadence (~840 files/day).
28. ~~No cross-validation that `capsules/*/capsule.toml` package sets stay consistent
    with each other or with `versions.toml`.~~ **RESOLVED (2026-08-29)**: added
    `scripts/verify-capsule-package-consistency.py` (package-name/`versions.toml`
    cross-check, `packages`/`required_modules` length parity, ash-capsule package-set
    nesting, `fixture`/`version_key` existence), wired as a gating `validate-contracts`
    job in `.github/workflows/build-capsules.yml`. It found a real bug on first run --
    see `docs/errc-8020-vital-few.md` §2 CREATE for details -- now fixed and green.
29. ~~`scripts/verify-postgres-capsule.sh` has no `run-offline.sh`-equivalent
    network-fenced wrapper.~~ **RESOLVED (2026-08-29)**: see item 20 above.
30. ~~No `docs/reference/vendors.md` documenting that ~95%+ of the vendored
    `swarmsh{,-v2}` tree is inert.~~ **RESOLVED (2026-08-29)**: added, compiled from
    this tracker's own items 7/8/17 (not independently re-verified against a live
    `vendors/` checkout).
31. ~~`CLAUDE.md`'s "four manufacturing surfaces" layout diagram omits `vendors/`
    entirely, despite `manufacturing/` and
    `capsules/autonomic-manufacturing/capsule.toml` hard-depending on it.~~
    **RESOLVED, with a naming correction (2026-08-29)**: the docs-governance fix pass
    added the six other missing surfaces to CLAUDE.md's layout but deliberately
    skipped adding `vendors/` after finding the string `vendors` appears nowhere
    under `manufacturing/` or `scripts/` — the directory actually read/written by
    `scripts/build-autonomic-manufacturing.sh` (via `CAPABILITY_SOURCE_ROOT`) and
    `.github/workflows/autonomic-manufacturing.yml` is `.capability-sources/`, not
    `vendors/`. Resolved by documenting `.capability-sources/` (the live name) in
    CLAUDE.md and `docs/reference/vendors.md` instead, with `vendors/`'s
    `.gitignore` entry noted as currently vestigial rather than hard-depended-on.
32. (from innovation-explorer, score 10) `ConformanceResult`/`Refusal`/
    `ProcessVariant` Ash resources are live-populated by the ingestor but not wired
    into `domain.ex`'s `tools`/`json_api`/`graphql` blocks — only `Qualification`/
    `CostObservation` get that exposure. Mirror the existing `list_qualifications`
    pattern. `control-plane/lib/chatgpt_cloud_control_plane/process_intelligence/resources.ex:154-208`,
    `domain.ex:34-58`.
33. (from innovation-explorer, score 10) `SwarmTeam`/`SwarmWorkItem` velocity
    aggregate (`control-plane/lib/chatgpt_cloud_control_plane/process_intelligence/swarm_team.ex:1-59`)
    has zero consumers — not in any LiveView, MCP tool, or `mcp-tools.md`.
34. (from innovation-explorer, score 10) `scripts/project_memory_proxy.py` supports
    `memory.query`/`memory.archive`/`memory.delete` but the MCP tool table only wraps
    `read`/`upsert`/`snapshot`/`list_project_items` — no `archive_dfcm_memory` /
    `delete_dfcm_memory` / `query_dfcm_memory` MCP tools exist.
35. (from innovation-explorer, score 9) `vendors/swarmsh-v2` emits OTEL coordination
    events that never reach the control-plane's OCEL ingest endpoint — the vendored
    coordination layer and the OCEL projection service don't talk to each other.

## Parked (pre-existing, from the domain review — genuinely ambiguous)

- `manufacturing/.ggen/keys/` and `.ggen-v2/receipt-log.jsonl` — untracked; unclear if
  intentionally ephemeral or should be gitignored explicitly.
- `SecretCredential` resource omits JSON:API/GraphQL extension — looks
  correct-by-design (secrets shouldn't be API-exposed) but unconfirmed.
- `bcrypt_elixir` dep — no direct usage found; possibly transitive from unused
  `ash_authentication`.
- `capsules/process-intelligence/capsule.toml` pins a different OTP/Elixir runtime
  than root `versions.toml` — may be intentional (pins external subject repos' own
  toolchain) but undocumented.
- `docs/reference/r48-independent-consumer.md` cites external `ggen-marketplace` SHAs
  unverifiable from this repo alone.
- `project-memory/` README's documented standings (`ALIVE/REFUSED/BLOCKED/UNKNOWN/
  BUILD_BROKEN`) don't match what's on disk (`PARTIAL_ALIVE`, `RUNNING`, `COMPLETE`,
  `REQUALIFYING` all appear) — doc vs. reality drift, unclear which is authoritative.
- `vendors/swarmsh{,-v2}` CHANGELOGs look like genuine upstream release notes —
  plausible but unconfirmable without upstream HEAD access.
- ~~Several `scripts/*.sh`/`*.py` are non-executable while siblings are `+x` — may be
  intentional convention or oversight.~~ **RESOLVED (2026-08-29)**: oversight, not
  intentional — every invocation of the 6 affected scripts (all in `.github/workflows/`
  and docs) called them via `bash scripts/foo.sh` explicitly, so the missing `+x` was
  never functionally load-bearing, just inconsistent with the rest of `scripts/`.
  `chmod +x` on all 6: `scripts/build-autonomic-manufacturing.sh`,
  `scripts/verify-autonomic-manufacturing.sh`,
  `scripts/install-local-control-macos{,-user}.sh`,
  `scripts/uninstall-local-control-macos{,-user}.sh`.

## Cycle 1 (2026-08-29, post 28-branch-merge audit)

A 7-surface parallel audit + bounded-fix pass (`claude/zoela-ultracode-merge-finish-8ye7ov`,
following the branch merge that formed this pass's starting tree) reverified every
Cycle 0 item still relevant (folded into the strikethroughs above) and found new
issues introduced by the merge itself. Fixed items are described inline in each
fix's commit; **two are CRITICAL and were deliberately left unfixed** — both need a
human decision or an Elixir/Erlang toolchain (unavailable in the sandbox this cycle
ran in), not a blind mechanical patch:

1. **Migration collision, control-plane** — two migrations both
   `create table(:swarm_work_items, ...)` with incompatible column sets:
   `20260826000000_create_swarm_coordination_tables.exs` (plain-Ecto schema
   `ChatGPTCloud.SwarmCoordination.WorkItem`, backing the raw HTTP SwarmSH JSON API)
   and `20260826173302_add_swarm_resources.exs` (Ash resource
   `ChatGPTCloud.ProcessIntelligence.SwarmWorkItem`, generated via
   `mix ash_postgres.generate_migrations`, tested by
   `test/chatgpt_cloud/process_intelligence/swarm_test.exs`). Both run in timestamp
   order against every fresh database; the second fails with Postgres `42P07`
   (relation already exists) — `mix ecto.migrate` on a clean database is
   `BUILD_BROKEN` today. Two independently-developed "swarm work" features collided
   on the same table name during the branch merge. Fix needs a real decision (which
   resource keeps `swarm_work_items`, what the other one's table should be renamed
   to) plus regenerating the Ash migration properly (`mix ash_postgres.generate_migrations`,
   never hand-edited) — not attempted blind with no compiler available to verify it.
2. **`local-control-bus` branch is stale, missing the mandatory approval gate** —
   `scripts/install-local-control-macos{,-user}.sh` clone/checkout the
   `local-control-bus` branch by default (`CHATGPT_LOCAL_CONTROL_BRANCH` env var
   overrides it) and launchd is configured to execute
   `scripts/local_control_agent.py` **from that branch's checkout**, not from
   `main`/this branch. `local-control-bus`'s last commit (2026-08-25 09:02) predates
   the entire mandatory-approval-gate feature added later the same day (22:12-22:17):
   no `ApprovalStore`, no `requires_approval`, no approve/deny/list-pending, no
   gating in `process_pending`. `local-control/AGENTS.md`'s "Requirement 9 ...
   deliberately unbypassable" language describes the gate that exists only on
   main/this branch. **Concretely: anyone who runs the installer today gets an agent
   that executes every admitted operation immediately with zero local human
   confirmation**, contradicting the documented safety guarantee. No workflow syncs
   `main` → `local-control-bus`, so nothing catches this drift automatically. Not
   fixed here because the correct remedy (sync the approval-gate code onto
   `local-control-bus`, or restructure so the installer's default branch is the
   synced/safe one) means pushing to a branch other than this session's designated
   one — a decision for whoever owns that branch, not a unilateral fix from this
   pass. Flagged prominently because it is a real, currently-live security gap, not
   a cosmetic one.

Also found and left open (non-critical, needs judgment or a toolchain this pass
didn't have): `capsules/process-intelligence/README.md` documents subject commit
SHAs that no longer match `capsules/process-intelligence/capsule.toml`'s actual
pins (doc drift, not a functional break — the build trusts `capsule.toml`); 143
files under `ggen/paas/` + `ggen/capability-lineage/` (SHACL-shaped runtime-admission
and capability-lineage RDF guards, ~100 of them SHACL) are entirely orphaned — no
script, workflow, or doc anywhere references them; `control-plane/lib/.../runtime_contracts/`
(107 lib + 54 test files) uses namespace `ChatGPTCloudControlPlane.RuntimeContracts.*`
while every other module in the app uses `ChatGPTCloud.*` — internally consistent,
compiles fine as far as static reading can tell, but an unexplained two-convention
split, too large a rename (~161 files) to do blind without a compiler.

Fixed this cycle (see the corresponding commit for detail): capsule builds were
silently dropping `emit-ocel-capsule-event.sh` from 6 of 8 capsule kinds' staged
`scripts/`, disabling OCEL observability emission for each (`|| true` made this
silent, not `BUILD_BROKEN`); `control-plane/config/dev.exs` was missing
`browser_auth_required: false`, meaning any browser route in `mix phx.server`
dev mode crashed with `ArgumentError` (per this repo's own README-documented dev
workflow); the `/mcp` router only forwarded 4 of 16 declared AshAi tools, silently
contradicting `README.md`'s documented "Project Two semantic PaaS"/"Vision 2030"
MCP surface; `local-control/receipt.schema.json` allowed an unused
`PENDING_APPROVAL` standing no code path ever emits; two `Refused` exception paths
in `scripts/local_control_agent.py` weren't recorded in the local replay ledger,
so the README's "deleting a receipt cannot silently authorize replay" invariant
didn't literally hold for those two paths; `.github/workflows/ggen-ecosystem-ocel-consumer.yml`'s
push trigger was scoped to a now-merged feature-branch name rather than `main`.

## See Also

- `docs/innovation-exploration-v26.9.1-cycle-report.md` — the innovation-explorer
  cycle report items 32-35 above are drawn from.
- `~/.claude/skills/errc-cycle/SKILL.md` — the process this tracker feeds.
