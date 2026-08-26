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
- No `docs/reference/vendors.md` documents that ~95%+ of the vendored swarmsh{,-v2} tree is inert (only 2 files load-bearing)
- `manufacturing/templates/capability-lock.json.tera` hardcodes release/authority-ceiling literals instead of deriving from ontology triples
- `scripts/verify-postgres-capsule.sh` has no `run-offline.sh`-equivalent network-fenced wrapper
- `CLAUDE.md`'s "four manufacturing surfaces" diagram omits `vendors/` entirely
- No script cross-validates `capsules/*/capsule.toml` package sets against `versions.toml`

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

## 4. Recommended next action

**Execute rank #1 (item 24):** Add a `> **Security:**` callout block to the top of the
"Auth" section in `docs/reference/mcp-tools.md`, stating that the single bearer token
(`OCEL_INGEST_TOKEN`) is the sole gate for OCEL ingestion, JSON:API, GraphQL, and all
6 MCP tools — including the `upsert_dfcm_memory` write action — and that anyone
holding it has full read/write reach across all four surfaces. Docs-only edit, no
code change, effort 1, highest leverage in the backlog.
