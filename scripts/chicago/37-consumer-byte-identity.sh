#!/usr/bin/env bash
set -euo pipefail
# prove every second-consumer product is byte-identical.
while IFS= read -r p; do
 cmp "$CONSUMER_A/manufacturing/generated/$p" "$CONSUMER_B/manufacturing/generated/$p"
 test "$(sha256sum "$CONSUMER_A/manufacturing/generated/$p" | awk '{print $1}')" = "$(sha256sum "$CONSUMER_B/manufacturing/generated/$p" | awk '{print $1}')"
done <"$CHICAGO_ROOT/files-a.txt"
test "$DIGEST_FIRST" = "$DIGEST_INDEPENDENT"
printf 'CHICAGO_PROBE ALIVE edge=37-consumer-byte-identity\n'
