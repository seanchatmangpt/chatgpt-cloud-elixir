# chatgpt-cloud-elixir: triage 17 PR-less unmerged remote branches

- Standing: OPEN
- Created: 2026-09-19 (v26.9.19 gh survey wave)
- Source: origin branches not merged into `main` with no open PR
- Evidence: `git branch -r --no-merged origin/main`: automation/cell4-ggen-ocel-20260826-1937 automation/fanout-cell1-20260826t130200z-control automation/measure-20260826-0202 automation/measure-r4-memory automation/portfolio-20260826t0150z automation/select-develop-20260825T1927Z automation/select4-memory-20260825 chatgpt/swarmsh-json-work-control claude/ultracode-branch-merge-avym0d claude/zoela-ultracode-merge-finish-8ye7ov explore-memory-20260825 feat/manufacturing-ocel-emission feat/v26.8.25-autonomic-manufacturing local-control-bus measure-r44-memory project-memory/implement-20260826t023800z project2/ws2-claim-20260827-2008

## Work to complete
- Triage each branch: land (open a PR) or delete (`git push origin --delete <branch>`). Work in batches; record decisions in History.

## Acceptance
- `git branch -r --no-merged origin/main` is empty after `git fetch --prune`.

## History
- 2026-09-19 | OPEN | survey found 17 PR-less branches | full list above | triage pending
