# 80/20 ERRC — Vital Few

**Repo:** `/Users/sac/chatgpt-cloud-elixir`
**Date:** 2026-08-26

This is the 80/20 cut of a larger ERRC (Eliminate/Reduce/Raise/Create) backlog: not
the full list of confirmed-real findings, but the small number of items that carry
most of the leverage. Ranked by impact/effort (leverage), these four items dominate
the backlog's total value — one closes a live security-documentation gap on the
single credential gating OCEL/DfCM/GraphQL/JSON:API, and three are low-effort,
concrete cleanups (dead script, missing precommit gate, undiagnosable JSON failures).
Everything else in the confirmed-real backlog is lower leverage and listed by title
only in section 3.

> **2026-08-29 reverify (post branch-merge):** all four Vital Few items below were
> independently closed by other branches merged into `claude/zoela-ultracode-merge-finish-8ye7ov`
> before this reverify ran. Confirmed directly against the merged tree (evidence per
> item below) rather than assumed from commit messages. No code changes were needed
> for any of the four; this pass only updates their status here.

## 0. Vital Few status (reverified 2026-08-29)

| Rank | Item | Status | Evidence |
|---|---|---|---|
| 24 | `mcp-tools.md` security callout | **DONE** | `docs/reference/mcp-tools.md` lines 30-34 carry the exact `> **Security:**` callout this item proposed. |
| 19 | `mix.exs` precommit `--cover`/`dialyzer` | **DONE** | `control-plane/mix.exs` `precommit` alias (~line 107) already runs `"format --check-formatted"`, `"compile --warnings-as-errors"`, `"chatgpt_cloud.ecosystem.verify"`, `"test --cover"`, `"dialyzer"`. Not re-run here — no Elixir/OTP toolchain is installed in this sandbox — so pass/fail of the suite itself is UNKNOWN, only that the gate is configured. |
| 25 | JSON parse diagnosability | **DONE** | `scripts/project_memory_proxy.py` `main()` has a dedicated `except json.JSONDecodeError as exc:` branch (reason `MALFORMED_REQUEST_JSON`, `error.details` with line/column/char) distinct from the generic `except Exception` (`UNHANDLED_PROXY_FAILURE`) branch. Verified by reading the source directly; `python3 -m pytest tests/` (57 passed, 9 subtests) covers this module. |
| 3 | `scripts/manufacturing-sync-and-emit.sh` dead script | **DONE** | File does not exist in the tree; already correctly marked resolved in `docs/errc-tracker.md` item 3. |

## 1. Vital Few (ranked by leverage)

| Rank | Quadrant | Item | Impact | Effort | Leverage | Proposed Action |
|---|---|---|---|---|---|---|
| 24 | RAISE | `docs/reference/mcp-tools.md` documents the single bearer token gating OCEL/DfCM/GraphQL/JSON:API with no security callout | 3 | 1 | 3 | Add a `> **Security:**` callout at the top of the "Auth" section stating this one token gates OCEL ingestion, JSON:API, GraphQL, and all 6 MCP tools (incl. the DfCM-memory write action). Docs-only change. |
| 19 | RAISE | `mix.exs` precommit alias has no `--cover` / `dialyzer` step | 2 | 1 | 2 | Add `"test --cover"`/`"dialyzer"` to the precommit alias; run for real and report actual pass/fail. |
| 25 | RAISE | 9 project-memory receipts `BUILD_BROKEN` from unhandled JSON parse exceptions (stray trailing brace) | 2 | 1 | 2 | Add a distinct `JSONDecodeError` branch in `project_memory_proxy.py` for diagnosability. |
| 3 | ELIMINATE | `scripts/manufacturing-sync-and-emit.sh` is a dead script — zero external references repo-wide | 2 | 1 | 2 | `git rm scripts/manufacturing-sync-and-emit.sh` and update/remove the corresponding line in `docs/errc-tracker.md`; or if intended for use, wire it into CI/Makefile. |

**#24 evidence (highest-leverage item):** Router (`control-plane/lib/chatgpt_cloud_control_plane_web/router.ex:15-60`) pipes `/api`, `/graphql`, and `/mcp` through one `:api` pipeline gated solely by `ChatGPTCloudWeb.OcelAuth` — a single shared bearer token (`OCEL_INGEST_TOKEN`). `docs/reference/mcp-tools.md` (38 lines) has zero matches for `grep -in "warning|security|⚠"` — verified directly — despite naming the credential that secures write access to DfCM memory plus JSON:API/GraphQL.

## 2. Everything else (confirmed real, lower leverage — title only)

**CREATE**
- ~~No `docs/reference/vendors.md` documents that ~95%+ of the vendored swarmsh{,-v2} tree is inert (only 2 files load-bearing)~~ **DONE (2026-08-29)**: added `docs/reference/vendors.md`, compiled from this tracker's existing evidence (not re-verified against a live `vendors/` checkout, which isn't present in this sandbox).
- `manufacturing/templates/capability-lock.json.tera` hardcodes release/authority-ceiling literals instead of deriving from ontology triples — **still open**, deliberately not attempted: fixing it needs a new/extended SPARQL query plus a `ggen sync run` to confirm the template still renders, and no `ggen` binary is available in this sandbox to verify that.
- ~~`scripts/verify-postgres-capsule.sh` has no `run-offline.sh`-equivalent network-fenced wrapper~~ **DONE (2026-08-29)**: added `scripts/run-postgres-offline.sh` (mirrors `run-offline.sh`'s network-fencing), wired into `build-postgres-capsule.sh` staging. `bash -n` clean; not run end-to-end (no built capsule in this sandbox).
- `CLAUDE.md`'s "four manufacturing surfaces" diagram omits `vendors/` entirely — **still open** (also now omits several other top-level surfaces the 2026-08-29 branch merge added: `ggen/`, `ggen.toml`, `ontology/`, `templates/`, `local-control/`, `verification/`, `tests/`; left for a dedicated docs pass covering the whole layout section at once rather than one omission at a time).
- ~~No script cross-validates `capsules/*/capsule.toml` package sets against `versions.toml`~~ **DONE (2026-08-29)**: added `scripts/verify-capsule-package-consistency.py`, wired into `.github/workflows/build-capsules.yml` as a `validate-contracts` job gating `build`. Running it against the current tree found and fixed a real, previously-undetected gap: `capsules/ash-postgres/capsule.toml` and `capsules/ash-phoenix/capsule.toml` both listed `spark`/`reactor`/`igniter` in `packages` but omitted the corresponding `Spark`/`Reactor`/`Igniter` from `required_modules` — meaning their generated capsule acceptance test (`scripts/build-capsule.sh`'s `CapsuleModulesTest`) never actually asserted those three modules loaded. Fixed both; verifier now passes clean (`CAPSULE_PACKAGE_CONSISTENCY=ALIVE capsules=8`).

**ELIMINATE**
- `Ecosystem.receipt/0` falsely reports AshAuthentication as ALIVE via `Code.ensure_loaded?` alone
- `scripts/verify-autonomic-manufacturing.sh` checks the wrong vendor path (`$ROOT/swarmsh/` instead of `vendors/swarmsh/`) — cannot pass as written
- False "RDF/SHACL" framing — no SHACL shapes exist anywhere in `manufacturing/`
- `capsules/process-intelligence/verify-capsule.sh` is an 85-line copy-paste fork of `scripts/verify-capsule.sh` (72 lines)

**RAISE**
- `verifier/verify_manifest.exs` validates via `String.contains?` substring search, not real JSON parsing
- `manufacturing/ontology.ttl` models 3 classes but only 1 (`CapabilitySource`) is ever queried by `manufacturing/queries/sources.rq`

**REDUCE**
- `ChatGPTCloud.Ecosystem.receipt/0` conflates 3 unrelated concerns in one untyped function
- `vendors/swarmsh/backlog.yaml` is over a year stale, unrelated to this repo's actual work
- `scripts/verify-capsule.sh` and `capsules/process-intelligence/verify-capsule.sh` share ~70% logic that should be one sourced helper
- `project-memory/` JSON formatting drifted (minified early files vs. pretty-printed later files)

## 3. Confirmed stale / already resolved (reverify pass)

| # | Quadrant | Claim | Finding |
|---|---|---|---|
| 8 | ELIMINATE | `vendors/swarmsh` and `vendors/swarmsh-v2` are unpinned — no commit SHA/tag/lockfile | **False as stated.** `manufacturing/ontology.ttl` declares exact pinned SHAs for both vendors (`745008438b9493d31e8af3735ad6116ac01c150f`, `02e5eaae14bd03a832c0f031acc56c6d4db3845e`); `manufacturing/generated/capability-lock.json` restates the same pins; real `git rev-parse HEAD` in both checkouts matches exactly, both clean. `vendors/` is deliberately gitignored (external reference repos, not submodules) per `docs/how-to/regenerate-autonomic-manufacturing-lock.md`. Residual (narrower, not part of the original claim): each checkout HEAD is on a named branch, not detached, so a stray `git pull` inside `vendors/` could drift silently with no automated check. |
| 9 | ELIMINATE | `scripts/verify-autonomic-manufacturing.sh` checks the wrong vendor path (`$ROOT/swarmsh/` instead of `vendors/swarmsh/`) — cannot pass as written | **Misdiagnosed.** `$ROOT` in this script is `$(dirname "${BASH_SOURCE[0]}")/..` evaluated *inside an installed/extracted capsule*, not this source repo — it is the capsule's own root, not `chatgpt-cloud-elixir/`. `scripts/build-autonomic-manufacturing.sh` stages the SwarmSH source at `$STAGE/swarmsh` and `$STAGE/swarmsh-v2` (`mkdir -p "$STAGE/swarmsh" "$STAGE/swarmsh-v2"` then `git archive` into each), and that `$STAGE` becomes the capsule root — so `$ROOT/swarmsh/coordination_helper.sh` in the verify script is exactly where the build script puts it. `vendors/swarmsh/` is a *different*, build-time-only, repo-side location (this repo's own `.gitignore`d checkout used as one of several possible `CAPABILITY_SOURCE_ROOT` inputs) that intentionally does not exist inside a shipped, relocatable capsule. The two scripts are internally consistent with each other; not reproduced. (End-to-end pass/fail is still UNKNOWN here — no `ggen` binary or vendored SwarmSH source is present in this sandbox to actually run the build — but the specific "wrong path" claim does not hold up against the source.) |

## 4. Recommended next action (reverified 2026-08-29)

All four Vital Few items (rank 24, 19, 25, 3) are now **DONE** — see section 0 above.
Next-highest leverage remaining, from section 2: `ChatGPTCloud.Ecosystem.receipt/0`
(`control-plane/lib/chatgpt_cloud_control_plane/ecosystem.ex`) still rolls
`AshAuthentication`/`AshAuthentication.Phoenix` into its `standing: "ALIVE"` gate via
bare `Code.ensure_loaded?/1` with no usage check, while real auth is hand-rolled
Basic/bearer plugs (`ChatGPTCloudWeb.OcelAuth`) — still reproduces directly against
the merged tree. Fixing it safely (Elixir) needs an actual `mix test`/`mix dialyzer`
run to confirm no regression; no Elixir/OTP toolchain was available in the sandbox
this reverify ran in, so that fix is left for an environment that can compile and
run the control-plane test suite rather than applied unverified.
