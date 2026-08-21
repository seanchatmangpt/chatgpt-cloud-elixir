#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck disable=SC1091
source "$ROOT/activate"

echo "capsule_root=$ROOT"
echo "manifest_sha256=$(sha256sum "$ROOT/manifest.json" | awk '{print $1}')"
echo "erl=$(command -v erl)"
echo "elixir=$(command -v elixir)"
echo "mix=$(command -v mix)"
echo "otp=$(erl -noshell -eval 'io:format("~s", [erlang:system_info(otp_release)]), halt().')"
echo "elixir_version=$(elixir -e 'IO.write(System.version())')"
echo "mix_version=$(mix --version | sed -n 's/^Mix //p' | head -1)"
echo "--- manifest ---"
cat "$ROOT/manifest.json"
