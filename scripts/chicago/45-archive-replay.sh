#!/usr/bin/env bash
set -euo pipefail
# extract the manufactured archive and replay its product digest.
mkdir -p "$CHICAGO_ROOT/archive-replay"
tar -xf "$CHICAGO_ROOT/products-a.tar" -C "$CHICAGO_ROOT/archive-replay"
replayed="$(cd "$CHICAGO_ROOT/archive-replay/generated" && find . -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum | awk '{print $1}')"
test "$replayed" = "$DIGEST_FIRST"
cmp "$CHICAGO_ROOT/archive-replay/generated/capability-lock.json" "$CONSUMER_A/manufacturing/generated/capability-lock.json"
printf 'CHICAGO_PROBE ALIVE edge=45-archive-replay\n'
