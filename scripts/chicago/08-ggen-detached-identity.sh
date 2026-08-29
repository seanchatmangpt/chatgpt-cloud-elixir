#!/usr/bin/env bash
set -euo pipefail
# prove the constructor executes from its exact detached commit.
test "$(git -C "$GGEN_DIR" rev-parse HEAD)" = "$GGEN_SHA"
test -z "$(git -C "$GGEN_DIR" branch --show-current)"
git -C "$GGEN_DIR" cat-file -e "$GGEN_SHA^{commit}"
test "$(git -C "$GGEN_DIR" rev-parse "$GGEN_SHA^{tree}")" = "$(git -C "$GGEN_DIR" rev-parse HEAD^{tree})"
printf 'CHICAGO_PROBE ALIVE edge=08-ggen-detached-identity\n'
