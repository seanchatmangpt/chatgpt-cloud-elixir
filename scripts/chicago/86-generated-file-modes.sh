#!/usr/bin/env bash
set -euo pipefail
for c in "$CONSUMER_A" "$CONSUMER_B"; do for p in "$c"/manufacturing/generated/*; do test -f "$p" -a -s "$p"; test "$(stat -c %a "$p")" -ge 600; done; test "$(find "$c/manufacturing/generated" -maxdepth 1 -type f | wc -l)" -eq 2; done
