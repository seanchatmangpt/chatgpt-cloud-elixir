#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORLD="$ROOT/harness/world.json"
OUT="$ROOT/harness/output"
mkdir -p "$OUT"

run_probe() {
  local subject="$1"
  local script="$2"
  local log="$3"
  (
    cd "$ROOT/subjects/$subject"
    MIX_ENV=test mix run "$ROOT/harness/$script" "$WORLD"
  ) 2>&1 | tee "$log"
}

run_probe ash_r2rml ash_probe.exs "$OUT/ash-probe.log"
run_probe ex4pm ex4pm_probe.exs "$OUT/ex4pm-probe.log"

ASH_JSON="$(sed -n 's/^PROCESS_LAB_JSON=//p' "$OUT/ash-probe.log" | tail -1)"
EX4PM_JSON="$(sed -n 's/^PROCESS_LAB_JSON=//p' "$OUT/ex4pm-probe.log" | tail -1)"
[[ -n "$ASH_JSON" ]] || { echo "BUILD_BROKEN: ash_r2rml probe emitted no process JSON" >&2; exit 65; }
[[ -n "$EX4PM_JSON" ]] || { echo "BUILD_BROKEN: ex4pm probe emitted no process JSON" >&2; exit 65; }
printf '%s\n' "$ASH_JSON" > "$OUT/ash.json"
printf '%s\n' "$EX4PM_JSON" > "$OUT/ex4pm.json"

(
  cd "$ROOT/subjects/ex4pm"
  MIX_ENV=test mix run "$ROOT/harness/compare.exs" "$ROOT" "$OUT/ash.json" "$OUT/ex4pm.json"
)
