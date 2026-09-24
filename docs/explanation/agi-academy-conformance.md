# AGI best practices: Academy rail conformance

"AGI best practices" here means the ecosystem's own standard, the **Chatman Ecosystem AGI
Academy** (`seanchatmangpt/chatman-ecosystem`, `catalog/agi-academy.toml`, release v26.9.8).
It is not a generic checklist. The Academy qualifies autonomous *candidates*. This repository
is an *execution rail* those candidates run on, so it conforms by enforcing every Academy
invariant and terminal refusal with guards that execute. It never issues credentials.

```bash
python3 scripts/verify-agi-conformance.py --receipt agi-conformance-receipt.json
```

## How it is built

| Piece | Role |
| --- | --- |
| `governance/agi-academy/` | Byte-identical reuse of the Academy manifest and its verifier, pinned by source SHA and SHA-256 in `PROVENANCE.toml`. The court refuses any drift. |
| `governance/agi-academy-conformance.toml` | Maps each of the 8 invariants, 5 terminal refusals, and 11 modules to guards (commands) that must exit 0. |
| `governance/failure-ledger.toml` | Module 8: every observed failure has a classification, the transition that failed, the repair, and a permanent guard that executes. |
| `scripts/verify-agi-conformance.py` | The court. It checks structure (digests, coverage, and the Academy's own manifest validation, reused rather than re-implemented), runs every guard, and derives standing only from exit codes. Exit codes: 0 ALIVE, 3 PARTIAL_ALIVE, 2 REFUSED. |
| `.github/workflows/agi-conformance.yml` | Runs the court on every push and PR and uploads the receipt for 90 days. |

## Gaps the audit found and closed

- **Unreceipted production DO** (`zero_unreceipted_actuation`). `deploy-fly.yml` deployed with
  no receipt. It now emits and uploads a receipt on every attempt, including blocked and failed
  ones, with standing derived from the observed step outcomes.
- **Unreceipted graph mutation.** `refresh-capability-sources.py --write` now refuses to run
  without `--receipt`.
- **Advisory blindness** (Module 3, route known problems to machines). `scripts/check-advisories.py`
  and `advisory-watch.yml` check every `versions.toml` pin against OSV weekly and on pin
  changes. Replayed against the old pins, the guard flags all 9 vulnerable packages.
- **Failures that were only narrated.** The LFS budget failure, the vulnerable pins, the Ash
  3.33 config, and the README pin drift are now ledger entries with executing guards.

## What this does not claim

- It does not claim that any AGI graduated. A candidate's credential needs the candidate's own
  execution receipts, evaluated by the Academy verifier.
- It does not grant authority. The rail ceiling stays `CONSTRUCT_VERIFY`.
- A guard that exits 0 proves the property that guard checks. Whether that guard is adequate
  for its mapped claim is a reviewable judgement recorded in `mechanism`, not something the
  court asserts.

## Keeping it current

When the Academy moves, re-vendor both files from the ontology-pinned `chatman-ecosystem` SHA
and update `PROVENANCE.toml`. The court then refuses until every new module, invariant, or
refusal is mapped to a guard.
