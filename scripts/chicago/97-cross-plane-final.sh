#!/usr/bin/env bash
set -euo pipefail
test "$DIGEST_FIRST" = "$DIGEST_REPLAY" -a "$DIGEST_FIRST" = "$DIGEST_INDEPENDENT"; test "$(git -C "$CONSUMER_A" rev-parse HEAD)" = "$SUBJECT_SHA"; test "$(git -C "$GGEN_DIR" rev-parse HEAD)" = "$GGEN_SHA"; python3 -m json.tool "$CONSUMER_A/manufacturing/.ggen-v2/receipt.json" >/dev/null
