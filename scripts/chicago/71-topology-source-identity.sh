#!/usr/bin/env bash
set -euo pipefail
p="$CONSUMER_A/manufacturing/generated/autonomic-manufacturing.mmd"; for x in ggen ggen-create ggen-legacy ggen-marketplace ggen-spec-kit swarmsh swarmsh-v2; do grep -Fq "$x" "$p"; done; ! grep -q UNKNOWN "$p"
