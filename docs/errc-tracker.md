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

## Backlog (Cycle 0 — initial seed, unverified)

### ELIMINATE

1. "RDF/SHACL" framing is false — no SHACL shapes exist anywhere in `manufacturing/`.
   Evidence: `find manufacturing -iname "*shacl*"` → nothing; `ontology.ttl` has no
   `sh:` constraints.
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
7. `vendors/swarmsh` — ~264 files of dead weight (telemetry dumps, `.backup.*` copies
   of `coordination_helper.sh`, speculative arxiv-paper drafts). Only 2 files
   (`coordination_helper.sh`, `real_agent_coordinator.sh`) are actually load-bearing.
8. `vendors/swarmsh{,-v2}` are unpinned — no commit SHA/tag/lockfile, despite
   `AGENTS.md` mandating exact-SHA pinning for anything used by/against this repo.
9. `scripts/verify-autonomic-manufacturing.sh` checks the wrong vendor path
   (`$ROOT/swarmsh/` instead of the real `vendors/swarmsh/`) — confirmed BUILD_BROKEN
   by the repo's own evidence vocabulary; no top-level `swarmsh/` dir exists.

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
19. `mix.exs` `precommit` alias has no `mix test --cover` or `mix dialyzer` — the
    coverage gap in #18 is invisible to CI.
20. "Offline law" is only enforced via `scripts/run-offline.sh`; calling
    `verify-capsule.sh` directly can silently fetch from Hex while still stamping
    `receipt.json` with `hex_offline`. `verify-postgres-capsule.sh` has no
    offline-fenced entry point at all.
21. `verifier/verify_manifest.exs` validates manifests via `String.contains?`
    substring search, not real JSON schema validation (`verifier/verify_manifest.exs:5-14`).
22. 8 of `ash-full` capsule's 15 required packages (AshPhoenix/Postgres/JsonApi/
    Authentication/Oban/GraphQL/AI/Money/Cloak/Archival/StateMachine) are verified
    only by `Code.ensure_loaded?`, not one real functional exercise — only
    `fixtures/ash_ets_smoke` exists as a real fixture.
23. `manufacturing/ontology.ttl` models `cc:ManufacturingCapsule`,
    `cc:AutonomicManufacturingCapsule`, `cc:CONSTRUCT_VERIFY` but only 1 of 3 classes
    (`CapabilitySource`) is ever queried by `manufacturing/queries/sources.rq`.
24. `docs/reference/mcp-tools.md` documents the single bearer token gating
    OCEL/DfCM/GraphQL/JSON:API — the most security-load-bearing doc in the repo,
    filed as a plain "reference" page with no security callout.
25. 9 `project-memory/` receipts are `BUILD_BROKEN` from unhandled JSON parse
    exceptions in `scripts/project_memory_proxy.py` — no defensive shape validation,
    recurred repeatedly same day with no fix landing.

### CREATE

26. `manufacturing/templates/capability-lock.json.tera` hardcodes
    `"release": "26.8.25"` / `"authority_ceiling": "CONSTRUCT_VERIFY"` as template
    literals instead of deriving them from the ontology's own
    `cc:releaseVersion`/`cc:authorityCeiling` triples.
27. No pruning/archival/rotation policy anywhere for `project-memory/` — unbounded
    growth by construction at current cadence (~840 files/day).
28. No cross-validation that `capsules/*/capsule.toml` package sets stay consistent
    with each other or with `versions.toml`.
29. `scripts/verify-postgres-capsule.sh` has no `run-offline.sh`-equivalent
    network-fenced wrapper.
30. No `docs/reference/vendors.md` documenting that ~95%+ of the vendored
    `swarmsh{,-v2}` tree is inert.
31. `CLAUDE.md`'s "four manufacturing surfaces" layout diagram omits `vendors/`
    entirely, despite `manufacturing/` and
    `capsules/autonomic-manufacturing/capsule.toml` hard-depending on it.
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
- Several `scripts/*.sh`/`*.py` are non-executable while siblings are `+x` — may be
  intentional convention or oversight.

## See Also

- `docs/innovation-exploration-v26.9.1-cycle-report.md` — the innovation-explorer
  cycle report items 32-35 above are drawn from.
- `~/.claude/skills/errc-cycle/SKILL.md` — the process this tracker feeds.
