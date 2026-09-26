#!/usr/bin/env bash
set -euo pipefail
# prove anonymous consumers retain no credential material.
! git -C "$CONSUMER_A" config --local --get credential.helper >/dev/null
! git -C "$CONSUMER_B" config --local --get credential.helper >/dev/null
! git -C "$CONSUMER_A" config --local --get-regexp '^http\..*\.extraheader$' >/dev/null
! git -C "$CONSUMER_B" config --local --get-regexp '^http\..*\.extraheader$' >/dev/null
printf 'CHICAGO_PROBE ALIVE edge=05-subject-credential-exclusion\n'
