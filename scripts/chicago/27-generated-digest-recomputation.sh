#!/usr/bin/env bash
set -euo pipefail
# independently recompute the first production consequence digest.
recomputed="$(cd "$CONSUMER_A/manufacturing/generated" && find . -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum | awk '{print $1}')"
test "$recomputed" = "$DIGEST_FIRST"
[[ "$recomputed" =~ ^[0-9a-f]{64}$ ]]
printf '%s\n' "$recomputed" >"$CHICAGO_ROOT/generated.sha256"
printf 'CHICAGO_PROBE ALIVE edge=27-generated-digest-recomputation\n'
