#!/usr/bin/env bash
set -euo pipefail
# prove the subject remains reachable through anonymous Git transport.
origin="$(git -C "$CONSUMER_A" remote get-url origin)"
test "$origin" = "https://github.com/$SUBJECT_REPOSITORY.git"
env -u GITHUB_TOKEN -u GH_TOKEN git -c credential.helper= ls-remote --exit-code "$origin" "refs/heads/$SUBJECT_REF" | grep -q "^$SUBJECT_SHA"
printf 'CHICAGO_PROBE ALIVE edge=02-subject-public-transport\n'
