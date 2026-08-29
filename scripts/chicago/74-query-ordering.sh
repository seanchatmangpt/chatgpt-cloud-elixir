#!/usr/bin/env bash
set -euo pipefail
q="$CONSUMER_A/manufacturing/queries/sources.rq"; grep -Eq '^ORDER BY \?name$' "$q"; test "$(grep -c '^PREFIX ' "$q")" -eq 2; test "$(grep -c 'cc:CapabilitySource' "$q")" -eq 1
