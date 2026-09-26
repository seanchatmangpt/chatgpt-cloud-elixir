#!/usr/bin/env bash
set -euo pipefail
# prove constructor source identity is public and repository-bound.
test "$(git -C "$GGEN_DIR" remote get-url origin)" = "https://github.com/$GGEN_REPOSITORY.git"
env -u GITHUB_TOKEN -u GH_TOKEN git -c credential.helper= ls-remote --exit-code "https://github.com/$GGEN_REPOSITORY.git" "$GGEN_SHA" >/dev/null
! git -C "$GGEN_DIR" config --local --get-regexp '^http\..*\.extraheader$' >/dev/null
printf 'CHICAGO_PROBE ALIVE edge=09-ggen-public-origin\n'
