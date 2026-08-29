#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck disable=SC1091
source "$ROOT/scripts/lib/verify-capsule-common.sh"
NETWORK_MODE="${CAPSULE_NETWORK_MODE:-hex_offline}"
CFG="$ROOT/source/capsule.toml"
VERSIONS="$ROOT/source/versions.toml"

run_subject_acceptance() {
  local subject="$1"
  local subject_dir="$ROOT/subjects/$subject"
  local -a commands=()

  mapfile -t commands < <(python3 - "$CFG" "$subject" <<'PY'
import sys, tomllib
cfg = tomllib.load(open(sys.argv[1], "rb"))
for command in cfg["subjects"][sys.argv[2]]["consumer_acceptance"]:
    print(command)
PY
)

  [[ "${#commands[@]}" -gt 0 ]] || {
    echo "BUILD_BROKEN: no consumer_acceptance declared for $subject" >&2
    return 65
  }

  cd "$subject_dir"
  for command in "${commands[@]}"; do
    echo ">>> [$subject consumer] $command"
    bash -c "$command"
  done
}

verification_body() {
  capsule_verify_manifest_and_runtime
  run_subject_acceptance ash_r2rml
  run_subject_acceptance ex4pm
  cd "$ROOT"
  bash "$ROOT/harness/verify.sh"
}
capsule_run_logged verification_body

STANDING="$(capsule_standing_from_status "$STATUS")"
MANIFEST_SHA="$(capsule_manifest_sha)"
PROCESS_RECEIPT_SHA="missing"
[[ -f "$ROOT/harness/process-lab-receipt.json" ]] && PROCESS_RECEIPT_SHA="$(sha256sum "$ROOT/harness/process-lab-receipt.json" | awk '{print $1}')"
SOURCE_SHA="$(capsule_source_sha)"
RELEASE_VERSION="$(python3 - "$VERSIONS" <<'PY'
import sys, tomllib
print(tomllib.load(open(sys.argv[1], "rb"))["release"]["version"])
PY
)"
VERIFIED_AT="$(capsule_verified_at)"

cat > "$ROOT/receipt.json" <<EOF2
{
  "schema_version": 1,
  "phase": "consumer_replay",
  "source_sha": "$SOURCE_SHA",
  "release_version": "$RELEASE_VERSION",
  "capsule_name": "process-intelligence",
  "capsule_archive_sha256": "$ARCHIVE_DIGEST",
  "manifest_sha256": "$MANIFEST_SHA",
  "process_lab_receipt_sha256": "$PROCESS_RECEIPT_SHA",
  "network_mode": "$NETWORK_MODE",
  "acceptance_command": "declared subject consumer_acceptance commands + process-lab bridge",
  "acceptance_exit_code": $STATUS,
  "verified_at": "$VERIFIED_AT",
  "standing": "$STANDING",
  "replay": "CAPSULE_NETWORK_MODE=$NETWORK_MODE bash scripts/verify-capsule.sh"
}
EOF2
cat "$ROOT/receipt.json"
exit "$STATUS"
