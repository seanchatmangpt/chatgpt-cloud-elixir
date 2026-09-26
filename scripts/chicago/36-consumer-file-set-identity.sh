#!/usr/bin/env bash
set -euo pipefail
# prove both consumers produce the same artifact topology.
(cd "$CONSUMER_A/manufacturing/generated" && find . -type f -printf '%P\n' | sort) >"$CHICAGO_ROOT/files-a.txt"
(cd "$CONSUMER_B/manufacturing/generated" && find . -type f -printf '%P\n' | sort) >"$CHICAGO_ROOT/files-b.txt"
cmp "$CHICAGO_ROOT/files-a.txt" "$CHICAGO_ROOT/files-b.txt"
test "$(wc -l <"$CHICAGO_ROOT/files-a.txt")" -eq 2
printf 'CHICAGO_PROBE ALIVE edge=36-consumer-file-set-identity\n'
