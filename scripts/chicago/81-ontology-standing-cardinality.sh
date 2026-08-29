#!/usr/bin/env bash
set -euo pipefail
o="$CONSUMER_A/manufacturing/ontology.ttl"; test "$(grep -c '  cc:requiredStanding "' "$o")" -eq 7; grep -q 'exact-source-build-and-replay' "$o"; ! grep '  cc:requiredStanding ' "$o" | grep -q '""'
