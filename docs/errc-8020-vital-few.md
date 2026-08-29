# 80/20 ERRC — Vital Few (closed)

This was the original 80/20 cut of `docs/errc-tracker.md`'s Cycle 0 backlog: the
four highest-leverage items, ranked by impact/effort, out of the full confirmed-real
backlog. **All four are now resolved** — see `docs/errc-tracker.md`'s Resolved
section for current detail. Kept here only as a historical record of what the cut
identified and why, since a couple of other files still cite this page by name.

## Status (reverified 2026-08-29)

| Rank | Item | Resolved by |
|---|---|---|
| 24 | `docs/reference/mcp-tools.md` had no security callout on the single bearer token gating OCEL/DfCM/GraphQL/JSON:API | A branch merged into `claude/zoela-ultracode-merge-finish-8ye7ov` before this reverify ran. |
| 19 | `mix.exs` `precommit` alias had no `--cover`/`dialyzer` step | Same. |
| 25 | 9 `project-memory/` receipts `BUILD_BROKEN` from unhandled JSON parse exceptions, no diagnosability | Same. |
| 3 | `scripts/manufacturing-sync-and-emit.sh` was a dead script, zero references | Deleted 2026-08-26, before this cut was even written. |

At the time this cut was made, rank 24 was judged the single highest-leverage item
in the whole backlog: the router pipes `/api`, `/graphql`, and `/mcp` through one
`:api` pipeline gated solely by `ChatGPTCloudWeb.OcelAuth` — a single shared bearer
token (`OCEL_INGEST_TOKEN`) — and the doc naming that credential had zero security
callout despite it gating write access to DfCM memory plus JSON:API/GraphQL.

## See also

- `docs/errc-tracker.md` — the full current backlog (Open / Resolved / Misdiagnosed /
  Parked), including everything else this 80/20 cut set aside as lower-leverage.
