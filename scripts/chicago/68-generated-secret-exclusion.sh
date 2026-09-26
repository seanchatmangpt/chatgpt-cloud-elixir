#!/usr/bin/env bash
set -euo pipefail
for c in "$CONSUMER_A" "$CONSUMER_B"; do ! grep -RIE 'ghp_[A-Za-z0-9]+|github_pat_[A-Za-z0-9_]+|BEGIN .*PRIVATE KEY' "$c/manufacturing/generated"; test -s "$c/manufacturing/generated/capability-lock.json"; done
