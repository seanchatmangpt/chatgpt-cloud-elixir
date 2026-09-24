#!/usr/bin/env bash
# Resolve the bounded set of XaaS relay requests to execute, one path per line.
#
# Inputs come ONLY from the environment (never interpolated into shell text):
#   DISPATCH_PATH  optional workflow_dispatch request path
#   EVENT_NAME     github.event_name
#   BEFORE_SHA     github.event.before (may be all-zero or unreachable)
#   AFTER_SHA      github.sha
#
# Fences:
#   - a path must match ^xaas-runtime/requests/[A-Za-z0-9._-]+\.json$ (no
#     subdirectories, no '..'), be a regular file, and not be a symlink;
#   - a request whose receipt already exists is never re-executed (run.submit
#     is not idempotent), so push re-runs, job re-runs, edits, and dispatches of
#     a receipted request are no-ops; retry with a new request_id;
#   - when BEFORE_SHA is all-zero (new branch) or unreachable (force-push), the
#     set falls back to every unreceipted request on the tree instead of
#     silently resolving to zero.
set -euo pipefail

PATTERN='^xaas-runtime/requests/[A-Za-z0-9._-]+\.json$'

admissible() {
  local path="$1"
  [[ "$path" =~ $PATTERN ]] || { echo "REFUSED[REQUEST_PATH_OUT_OF_SCOPE] $path" >&2; return 1; }
  [[ "$path" != *..* ]] || { echo "REFUSED[REQUEST_PATH_OUT_OF_SCOPE] $path" >&2; return 1; }
  [[ ! -L "$path" ]] || { echo "REFUSED[REQUEST_PATH_SYMLINK] $path" >&2; return 1; }
  [[ -f "$path" ]] || { echo "REFUSED[REQUEST_PATH_MISSING] $path" >&2; return 1; }
}

unreceipted() {
  local path="$1" base
  base="$(basename "$path" .json)"
  if [[ -e "xaas-runtime/receipts/${base}.receipt.json" ]]; then
    echo "SKIPPED[ALREADY_RECEIPTED] $path" >&2
    return 1
  fi
}

candidates() {
  if [[ -n "${DISPATCH_PATH:-}" ]]; then
    admissible "$DISPATCH_PATH" || exit 2
    printf '%s\n' "$DISPATCH_PATH"
    return
  fi
  [[ "${EVENT_NAME:-}" == "push" ]] || return 0
  local before="${BEFORE_SHA:-}" after="${AFTER_SHA:?AFTER_SHA required}"
  if [[ -z "$before" || "$before" =~ ^0+$ ]] || ! git cat-file -e "${before}^{commit}" 2>/dev/null; then
    echo "NOTICE[BEFORE_UNRESOLVABLE] scanning all unreceipted requests" >&2
    git ls-tree -r --name-only "$after" -- xaas-runtime/requests/
  else
    git diff --name-only --diff-filter=AM "$before" "$after" -- xaas-runtime/requests/
  fi
}

candidates | sort -u | while IFS= read -r path; do
  [[ -n "$path" ]] || continue
  [[ "$path" =~ $PATTERN ]] || continue
  admissible "$path" || continue
  # Also applies to dispatch: a retry is a NEW request_id, never a re-execution.
  unreceipted "$path" || continue
  printf '%s\n' "$path"
done
