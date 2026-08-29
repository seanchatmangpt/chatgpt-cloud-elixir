#!/usr/bin/env bash
set -euo pipefail
q="$CONSUMER_A/manufacturing/queries/sources.rq"; for x in name repository sha role capitalClass executionMode standing; do grep -q "?$x" "$q"; done; grep -q SELECT "$q"; grep -q WHERE "$q"
