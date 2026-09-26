#!/usr/bin/env bash
set -euo pipefail
# prove full generation leaves tracked consumer source immutable.
git -C "$CONSUMER_A" diff --quiet
git -C "$CONSUMER_A" diff --cached --quiet
git -C "$CONSUMER_B" diff --quiet
git -C "$CONSUMER_B" diff --cached --quiet
printf 'CHICAGO_PROBE ALIVE edge=07-subject-source-immutability\n'
