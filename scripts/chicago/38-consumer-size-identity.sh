#!/usr/bin/env bash
set -euo pipefail
# prove independent products retain identical byte cardinality.
while IFS= read -r p; do
 test "$(stat -c %s "$CONSUMER_A/manufacturing/generated/$p")" -eq "$(stat -c %s "$CONSUMER_B/manufacturing/generated/$p")"
 test "$(stat -c %s "$CONSUMER_A/manufacturing/generated/$p")" -gt 0
done <"$CHICAGO_ROOT/files-a.txt"
test "$(du -sb "$CONSUMER_A/manufacturing/generated" | cut -f1)" -gt 0
printf 'CHICAGO_PROBE ALIVE edge=38-consumer-size-identity\n'
