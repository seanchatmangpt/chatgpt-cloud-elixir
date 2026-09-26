#!/usr/bin/env bash
set -euo pipefail
p="$CONSUMER_A/manufacturing/generated/autonomic-manufacturing.mmd"; test "$(grep -c '^  SRC[0-9].* --> C$' "$p")" -eq 7; for i in 1 2 3 4 5 6 7; do grep -q "^  SRC$i\[" "$p"; done
