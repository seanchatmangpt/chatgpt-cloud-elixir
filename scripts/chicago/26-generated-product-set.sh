#!/usr/bin/env bash
set -euo pipefail
# prove full sync emits exactly the declared product set.
mapfile -t actual < <(cd "$CONSUMER_A/manufacturing/generated" && find . -maxdepth 1 -type f -printf '%f\n' | sort)
test "${#actual[@]}" -eq 2
test "${actual[0]}" = autonomic-manufacturing.mmd
test "${actual[1]}" = capability-lock.json
test -s "$CONSUMER_A/manufacturing/generated/${actual[0]}"
printf 'CHICAGO_PROBE ALIVE edge=26-generated-product-set\n'
