#!/usr/bin/env bash
set -euo pipefail
# inspect the real deterministic archive for extraction-safe paths.
tar -tf "$CHICAGO_ROOT/products-a.tar" >"$CHICAGO_ROOT/products.list"
test -s "$CHICAGO_ROOT/products.list"
! grep -Eq '(^/|(^|/)\.\.(/|$))' "$CHICAGO_ROOT/products.list"
grep -q '^generated/capability-lock.json$' "$CHICAGO_ROOT/products.list"
grep -q '^generated/autonomic-manufacturing.mmd$' "$CHICAGO_ROOT/products.list"
printf 'CHICAGO_PROBE ALIVE edge=44-archive-path-safety\n'
