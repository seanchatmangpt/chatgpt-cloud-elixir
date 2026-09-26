#!/usr/bin/env bash
set -euo pipefail
a="$CONSUMER_A/manufacturing/generated/autonomic-manufacturing.mmd"; b="$CONSUMER_B/manufacturing/generated/autonomic-manufacturing.mmd"; cmp "$a" "$b"; test -s "$a"; ! grep -q $'\r' "$a"; test "$(tail -c1 "$a" | wc -l)" -eq 1
