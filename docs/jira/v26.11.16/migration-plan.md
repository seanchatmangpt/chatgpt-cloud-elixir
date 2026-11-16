# chatgpt-cloud-elixir migration plan v26.11.16

Standing: UNVERIFIED

## Identity
- Path: /Users/sac/chatgpt-cloud-elixir
- Remote: https://github.com/seanchatmangpt/chatgpt-cloud-elixir
- Branch: feat/xaas-fabric-elixir@404e46b0 (tracks origin/feat/xaas-fabric-elixir, in sync)
- Last commit: 2026-09-25 — "test(runtime): prove disposable provider survives transport
  extinction"
- Commits: 1930; size: 717 MB
- Languages/build: Elixir/Phoenix (control-plane/, xaas-runtime/), Python (scripts/, tests/,
  .pytest_cache), shell capsule builders, versions.toml
- Nested repos: none

## Observed state
- Dirty: 7 tracked — README.md, control-plane/.../process_intelligence/queries.ex,
  control-plane/.../router.ex, docs/how-to/xaas-ultracode-runtime.md, scripts/xaas-runtime.py,
  tests/test_xaas_runtime.py, xaas-runtime/README.md.
- Untracked: 124 — mostly control-plane/ (8 top paths), xaas-runtime/, docs/, vendors/, .zcode/.
- Ahead 0 / behind 0 on the current branch.
- Stash: 0.
- Unpushed/local branches (9): `claude/a2a-capabilities-2sEqrx` (no upstream),
  `feat/local-control-engage-26.9.23` (no upstream), `dfcm-memory/claude-mcp-junction`
  (upstream GONE — deleted on remote), `feat/capsule-ocel-emission` (behind 2), plus 5 that
  track origin cleanly.
- Build/cache dirs: `.capsule-build/` 140M, `vendors/` 23M, `dist/` 0B, `.pytest_cache`,
  `.benchmarks`. Most of the 717 MB is .git history + .capsule-build.
- Submodules: none.

## What it is
Portable, offline-capable Erlang/Elixir/Ash runtime capsules for restricted ChatGPT cloud
containers, plus an XaaS fabric runtime (WSS transport with GitHub Actions fallback) and a
Phoenix control plane with process-intelligence resources.

## Classification
ACTIVE (census agrees).

## Migration risk
- Lost if not copied: 7 dirty files of xaas-runtime/control-plane WIP, 124 untracked files
  (unknown value — likely control-plane resources + migrations), 2 branches with no upstream,
  1 branch whose remote branch was deleted (`dfcm-memory/claude-mcp-junction`).
- No .env or db files observed at depth 2. `.zcode/` is untracked tool state.
- Rating: HIGH.

## Recommended action
COMMIT-PUSH

1. `cd /Users/sac/chatgpt-cloud-elixir && git status --porcelain | head -60` — triage the 124
   untracked paths; add `.zcode/`, `.capsule-build/`, `.pytest_cache/` to .gitignore if absent.
2. `git add -A && git commit -m "wip(v26.11.16): xaas-runtime + control-plane process intelligence"`.
3. `git push origin feat/xaas-fabric-elixir`.
4. `git push -u origin claude/a2a-capabilities-2sEqrx feat/local-control-engage-26.9.23`.
5. DECISION: `dfcm-memory/claude-mcp-junction` — remote branch is gone. Re-push
   (`git push -u origin dfcm-memory/claude-mcp-junction`) or confirm merged and drop.
6. `git push origin feat/capsule-ocel-emission` after `git fetch` + review of the 2 behind.
7. `rm -rf .capsule-build dist .pytest_cache .benchmarks` — do not copy build artefacts.
8. `git branch -vv | grep -E 'ahead|gone|^\*? *[a-z/-]+ +[0-9a-f]+ [a-z]'` — must be empty.
9. New machine: `git clone https://github.com/seanchatmangpt/chatgpt-cloud-elixir`.

## First commands on the new machine
- `cd control-plane && mix deps.get && mix test`
- `cd xaas-runtime && mix deps.get && mix test`
- `python -m pytest tests/` (capsule/runtime Python tests)

## See Also
- ../v26.9.23/
- ../v26.9.19/
- /Users/sac/docs/jira/v26.11.16/README.md
