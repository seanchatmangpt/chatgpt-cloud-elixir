# 010 — local-control engage wave (v26.9.23)

- Date: 2026-09-23
- Goal: make Sean's laptop interact with ephemeral ChatGPT cloud instances through the
  bounded local-control transport: port the capability onto current main, prove it with
  courts + a local loopback, enroll the laptop, and run one real request→receipt round
  trip on `origin/local-control-bus`.
- Operator order: "Launch 10 default-agent to make it so that I can have my laptop
  interact with the ephemeral cloud instances."

## Bases

- Main base: `c5243335` (local main, ahead of origin).
- Capability source: `origin/local-control-bus` @ `a94fe298` (PR #11, base cb7d36d2 —
  489+ commits stale). Mechanical port commit `lc26923/base-port` carries ONLY:
  `local-control/**`, `scripts/local_control_agent.py`, `scripts/*local-control*.sh`,
  `tests/test_local_control_agent.py`, `tests/test_local_control_no_sudo.py`,
  `.github/workflows/local-control-ci.yml`. No stale deletions ride along.
- Wave integration branch: `feat/local-control-engage-26.9.23` (draft PR vs main, no merge
  without explicit operator request).

## Contract constants (bind every slice)

- Transport branch: `local-control-bus`. Requests: `local-control/requests/<request_id>.json`.
  Receipts: `local-control/receipts/<request_id>.receipt.json`. Schemas:
  `local-control/request.schema.json`, `local-control/receipt.schema.json`.
- Envelope: `request_id` (must equal file stem), `operation`, `machine: {id: "<hostname>" | "*"}`,
  optional `expires_at` (UTC ISO with timezone), `payload`. Refusal taxonomy:
  `OPERATION_NOT_ALLOWED | MACHINE_SCOPE_VIOLATION | REQUEST_EXPIRED | REPLAY_DETECTED |
  READ_PATH_NOT_ALLOWED | WRITE_PATH_NOT_ALLOWED | EXECUTABLE_NOT_ALLOWED |
  DESTRUCTIVE_OPERATION_DISABLED | REQUEST_ID_PATH_MISMATCH | ...`.
- Agent CLI: `serve --policy P [--once] [--poll-seconds N]`, `validate-policy --policy P`.
  Active policy lives OUTSIDE Git; Git carries examples/templates only.
- Receipt standings: `ALIVE | REFUSED | BUILD_BROKEN`. Host standing vocabulary:
  `UNKNOWN | PARTIAL_ALIVE | ALIVE | BLOCKED | BUILD_BROKEN | UNSUPPORTED | REFUSED_*`.
- Test runner: `/opt/homebrew/bin/python3 -m unittest` (stdlib unittest; no pytest).
  Agent code must stay compatible with system `python3` 3.9.

## Slices (exclusive file ownership; all branches off `lc26923/base-port`)

| # | branch | owns | acceptance |
|---|---|---|---|
| S01 | lc26923/s01-agent-adapt | scripts/local_control_agent.py, tests/test_local_control_agent.py | unittest green on 3.12 AND 3.9; `validate-policy` runs on example |
| S02 | lc26923/s02-installer-court | scripts/*local-control*.sh, tests/test_local_control_no_sudo.py | `bash -n` all 4; shellcheck clean or documented exceptions; no-sudo tests green |
| S03 | lc26923/s03-policy-template | local-control/policy.example.json, tests/test_local_control_policy.py | example loads via Policy; fences hold (no destructive, minimal ops) |
| S04 | lc26923/s04-ci-workflow | .github/workflows/local-control-ci.yml | YAML parses; steps reference paths that exist on this base |
| S05 | lc26923/s05-readme-runbook | local-control/README.md | enrollment runbook current for this base; links schemas + invariants |
| S06 | lc26923/s06-e2e-loopback | scripts/local_control_e2e_loopback.sh | loopback: temp bare transport → file request → agent `--once` → receipt + replay skip; exits 0 |
| S07 | lc26923/s07-instance-guide | local-control/CLOUD-INSTANCE-GUIDE.md | exact git-only commands an ephemeral cloud instance runs; envelope cheat sheet |
| S08 | lc26923/s08-falsifier-court | tests/test_local_control_falsifiers.py | adversarial court green: expired, machine mismatch, replay, unsupported op, destructive-off, path-outside-roots, executable-not-allowed, id/path mismatch |
| S09 | lc26923/s09-enroll-preflight | scripts/local_control_enroll_preflight.sh | runs green on this laptop; checks python3, git reachability of origin branch, launchd user paths, policy validate |
| S10 | lc26923/s10-request-cli | scripts/local_control_request.py, tests/test_local_control_request.py | CLI file/list/fetch; envelope matches schema + id==stem; tests green |

## Merge order

S01 → S02 → S03 → S04 → S08 → S10 → S06 → S09 → S05 → S07. Boundary after each merge:
`/opt/homebrew/bin/python3 -m unittest discover -s tests -p 'test_local_control*.py'`.
Red → reset that merge, record BLOCKED.

## Crown (post-integration, coordinator-executed)

1. `local_control_enroll_preflight.sh` green on this laptop.
2. Active policy installed at `~/.config/chatgpt-local-control/policy.json`
   (installer default path; read-only operations: system.snapshot, filesystem.list,
   filesystem.read; read_roots scoped to this repo; allow_destructive=false).
3. One real round trip on `origin/local-control-bus`: request commit (from laptop, standing
   in for a cloud instance) → agent `--once` → receipt commit on origin → replay shows skip.
4. LaunchAgent enrollment via the no-sudo installer only if 1–3 are green.

## History

- 2026-09-23T--Z | control | ticket written; wave scaffolded (base-port + 10 worktrees); standing=UNKNOWN
- 2026-09-24T06:15Z | wave | 10 default-agents dispatched in parallel (isolated worktrees); returned 8 ALIVE / 2 PARTIAL_ALIVE (dotted-form unittest shadow); commits: s01@850ce2de s02@d66a3de0 s03@70c9704b s04@e938e393 s05@c02fd3d1 s06@2cf41643 s07@bf4f0039 s08@02752036 s09@9549b70c s10@cb8f1f9f
- 2026-09-24T06:2xZ | integrate | 10/10 merges onto feat/local-control-engage-26.9.23, unittest boundary green after each; S08 court caught S01 ledger refactor (private .data) — repaired on owning branch via public on-disk contract (2ce8f94d→amended); integration commits: tests/__init__.py marker + README policy-path alignment; head 4d238d22
- 2026-09-24T06:26Z | crown | preflight 6/6 PASS; active policy ~/.config/chatgpt-local-control/policy.json (read-only, machine_id=Mac.lan); real round trip on origin/local-control-bus: request system.snapshot.20260924T062408Z.98d5 → ALIVE receipt on origin (fresh-clone witness) → replay skipped; LaunchAgent enrolled (pid 95669, state=running); cloud-side request filesystem.list.20260924T062624Z.948e processed by daemon → ALIVE receipt on origin ~20s, CLI fetch exit 0
- 2026-09-24T06:30Z | publish | branch pushed; draft PR #35 opened (base disclosure: branch sits on local main 489 ahead of origin/main, ticket 003); standing=ALIVE for the enrolled laptop↔transport rail at 4d238d22; standing=PARTIAL_ALIVE for origin/main convergence (489-commit landing is ticket 003, not this wave)
- 2026-09-24T07:0xZ | retire-topology | operator laws adopted: (1) repository topology is transport, never ontology — one canonical checkout, no worktrees/shadow clones; (2) LLM agents reduced to the edges only — machinery-first routing. Containment guard re-run (11/11 lc26923/* ancestors of feat==origin==4d238d22), then 12 wave worktrees removed, 11 slice branches deleted (tips recorded: 3a6fded3 850ce2de d66a3de0 70c9704b e938e393 c02fd3d1 2cf41643 bf4f0039 b2db2842 9549b70c cb8f1f9f), pruned; WORKTREES_BEFORE=12 WORKTREES_AFTER=0 UNIQUE_COMMITS_LOST=0. Laws persisted to session memory; repo AGENTS.md gained `## Topology law` section on the PR branch (c02779e2, pushed). Future waves: classify-and-route script first; mechanical classes → scripts/gates with receipts; LLM only at semantic edges, read-only fan-out, serialized writes in the canonical checkout.
