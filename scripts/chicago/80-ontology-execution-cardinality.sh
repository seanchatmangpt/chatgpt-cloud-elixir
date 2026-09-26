#!/usr/bin/env bash
set -euo pipefail
o="$CONSUMER_A/manufacturing/ontology.ttl"; test "$(grep -c '  cc:executionMode "' "$o")" -eq 7; grep -q 'compiled-binary' "$o"; ! grep '  cc:executionMode ' "$o" | grep -q '""'
