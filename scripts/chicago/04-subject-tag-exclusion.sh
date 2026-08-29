#!/usr/bin/env bash
set -euo pipefail
# prove bootstrap clones do not inherit mutable tag state.
test -z "$(git -C "$CONSUMER_A" tag --list)"
test -z "$(git -C "$CONSUMER_B" tag --list)"
! git -C "$CONSUMER_A" describe --tags --exact-match >/dev/null 2>&1
! git -C "$CONSUMER_B" describe --tags --exact-match >/dev/null 2>&1
printf 'CHICAGO_PROBE ALIVE edge=04-subject-tag-exclusion\n'
