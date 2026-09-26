#!/usr/bin/env bash
set -euo pipefail
# inspect the real generated topology as a nonempty textual artifact.
p="$CONSUMER_A/manufacturing/generated/autonomic-manufacturing.mmd"
test -s "$p"
test "$(wc -l <"$p")" -ge 2
grep -Eq 'graph|flowchart|sequenceDiagram|stateDiagram' "$p"
! grep -q $'\r' "$p"
printf 'CHICAGO_PROBE ALIVE edge=25-generated-topology-product\n'
