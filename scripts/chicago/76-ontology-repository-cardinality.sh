#!/usr/bin/env bash
set -euo pipefail
o="$CONSUMER_A/manufacturing/ontology.ttl"; test "$(grep -c '  cc:repository "seanchatmangpt/' "$o")" -eq 7; ! grep '  cc:repository ' "$o" | grep -vq '^  cc:repository "seanchatmangpt/[a-z0-9-]*" ;$'
