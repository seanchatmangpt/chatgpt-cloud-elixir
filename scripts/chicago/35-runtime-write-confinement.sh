#!/usr/bin/env bash
set -euo pipefail
# prove every untracked consequence stays in generated or receipt ownership.
for c in "$CONSUMER_A" "$CONSUMER_B"; do
 git -C "$c" status --porcelain --untracked-files=all | while IFS= read -r line; do
  case "$line" in
   "?? manufacturing/generated/"*|"?? manufacturing/.ggen-v2/receipt-log.jsonl") ;;
   *) echo "unowned consequence: $line" >&2; exit 1 ;;
  esac
 done
done
printf 'CHICAGO_PROBE ALIVE edge=35-runtime-write-confinement\n'
