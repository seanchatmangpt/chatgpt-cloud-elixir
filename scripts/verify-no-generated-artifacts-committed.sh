#!/usr/bin/env bash
# CLAUDE.md is explicit: "Generated capsule archives, manifests, checksums, receipts,
# and manufacturing/generated/* are build projections — never hand-edit them." This
# script makes that mechanically enforced instead of merely documented: it fails if
# any build-projection path is ever tracked by git, regardless of .gitignore (which
# only stops *future* accidental `git add`; it does nothing about a path that was
# already committed before the ignore rule existed).
#
# Usage: scripts/verify-no-generated-artifacts-committed.sh
# Exit codes: 0 = clean, 65 = BUILD_BROKEN (a projection path is tracked).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# Mirrors the "Build projections" block added to .gitignore. Kept as an explicit
# list (not a .gitignore read-back) so this check still works if .gitignore is
# ever edited incorrectly — the two are independent layers on purpose.
PATTERNS=(
  '^dist/'
  '^\.capsule-build/'
  '^\.capability-sources/'
  '^consumer/'
  '^transported/'
  '^manufacturing/generated/'
  '^verification-state/'
  '^state/'
  '^verification\.log$'
  '^receipt\.json$'
  '^build-receipt\.json$'
  '\.project-memory-runtime/'
)

REGEX="$(IFS='|'; echo "${PATTERNS[*]}")"
HITS="$(git -C "$ROOT" ls-files | grep -E "$REGEX" || true)"

if [[ -n "$HITS" ]]; then
  echo "BUILD_BROKEN: build-projection paths are tracked in git (must be manufactured, never committed):" >&2
  printf '  %s\n' "$HITS" >&2
  exit 65
fi

echo "GENERATED_ARTIFACTS_GUARD=ALIVE tracked_projection_paths=0"
