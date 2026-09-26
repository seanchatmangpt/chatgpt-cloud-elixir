#!/usr/bin/env bash
set -euo pipefail
# prove the production CLI exposes the admitted sync execution route.
"$GGEN_BIN" sync --help >"$CHICAGO_ROOT/ggen-sync-help.txt"
"$GGEN_BIN" sync run --help >"$CHICAGO_ROOT/ggen-sync-run-help.txt"
grep -qi 'sync' "$CHICAGO_ROOT/ggen-sync-help.txt"
grep -qiE 'run|execute|manifest' "$CHICAGO_ROOT/ggen-sync-run-help.txt"
printf 'CHICAGO_PROBE ALIVE edge=15-ggen-sync-entrypoint\n'
