#!/usr/bin/env bash
set -euo pipefail
"$GGEN_BIN" --help >"$CHICAGO_ROOT/help-again.txt"; "$GGEN_BIN" sync run --help >"$CHICAGO_ROOT/sync-help-again.txt"; test -s "$CHICAGO_ROOT/help-again.txt" -a -s "$CHICAGO_ROOT/sync-help-again.txt"; grep -qi sync "$CHICAGO_ROOT/help-again.txt"
