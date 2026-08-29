#!/usr/bin/env bash
set -euo pipefail
o="$CONSUMER_A/manufacturing/ontology.ttl"; test "$(grep -c '  cc:capitalClass "' "$o")" -eq 7; grep -q 'manufacturing-runtime' "$o"; ! grep '  cc:capitalClass ' "$o" | grep -q '""'
