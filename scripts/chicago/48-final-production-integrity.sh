#!/usr/bin/env bash
set -euo pipefail
# prove the complete production path closes without secret or identity drift.
test "$DIGEST_FIRST" = "$DIGEST_REPLAY"
test "$DIGEST_FIRST" = "$DIGEST_INDEPENDENT"
test "$MALFORMED_EXIT" -ne 0
test "$STALE_EXIT" -ne 0
test "$RECEIPT_LINES_REPLAY" -gt "$RECEIPT_LINES_FIRST"
! grep -RIE 'ghp_[A-Za-z0-9]+|github_pat_[A-Za-z0-9_]+' "$CONSUMER_A/manufacturing/generated" "$CONSUMER_B/manufacturing/generated"
test "$(git -C "$CONSUMER_A" rev-parse HEAD)" = "$SUBJECT_SHA"
printf 'CHICAGO_PROBE ALIVE edge=48-final-production-integrity\n'
