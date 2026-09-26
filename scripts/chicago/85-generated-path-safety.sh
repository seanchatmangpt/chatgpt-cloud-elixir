#!/usr/bin/env bash
set -euo pipefail
for c in "$CONSUMER_A" "$CONSUMER_B"; do while read -r p; do case "$p" in /*|*../*) exit 1;; esac; done < <(cd "$c/manufacturing/generated" && find . -type f -printf '%P\n'); test "$(find "$c/manufacturing/generated" -type l | wc -l)" -eq 0; done
