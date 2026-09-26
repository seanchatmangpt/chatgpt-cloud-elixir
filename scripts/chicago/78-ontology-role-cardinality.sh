#!/usr/bin/env bash
set -euo pipefail
o="$CONSUMER_A/manufacturing/ontology.ttl"; test "$(grep -c '  cc:role "' "$o")" -eq 7; grep -q 'deterministic semantic manufacturing engine' "$o"; ! grep '  cc:role ' "$o" | grep -q '""'
