#!/usr/bin/env bash
set -euo pipefail
o="$CONSUMER_A/manufacturing/ontology.ttl"; test "$(grep -c ' a cc:CapabilitySource ;' "$o")" -eq 7; for x in Ggen GgenMarketplace GgenCreate GgenLegacy GgenSpecKit SwarmSH SwarmSHV2; do grep -q "^cc:$x a cc:CapabilitySource" "$o"; done
