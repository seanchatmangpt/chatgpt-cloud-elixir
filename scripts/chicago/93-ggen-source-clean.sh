#!/usr/bin/env bash
set -euo pipefail
git -C "$GGEN_DIR" diff --quiet; git -C "$GGEN_DIR" diff --cached --quiet; test "$(git -C "$GGEN_DIR" rev-parse HEAD)" = "$GGEN_SHA"; test -z "$(git -C "$GGEN_DIR" branch --show-current)"
