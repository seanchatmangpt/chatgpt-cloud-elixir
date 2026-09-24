#!/usr/bin/env bash
# S06 (wave v26.9.23) — local-control full-loop e2e over a pure-local git loopback.
#
# Proves, without touching GitHub or any network:
#   temp bare transport remote  ->  request envelope commit on local-control-bus
#   -> agent checkout (pre-cloned, so ensure_checkout reuses it)
#   -> scripts/local_control_agent.py serve --once
#   -> receipt ALIVE committed + pushed back to the bare remote
#   -> second serve --once: replay skip, exactly one receipt, transport tip unchanged.
#
# Ticket: docs/jira/v26.9.23/010-local-control-engage.md (slice S06).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [ -x /opt/homebrew/bin/python3 ]; then
  PY=/opt/homebrew/bin/python3
else
  PY=python3
fi

PASS=0
FAIL=0

check() {
  local label="$1"
  shift
  if "$@"; then
    echo "PASS: $label"
    PASS=$((PASS + 1))
  else
    echo "FAIL: $label"
    FAIL=$((FAIL + 1))
  fi
}

# Hermetic git: no global/system config, no signing, no hooks, no prompts.
unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE || true
export GIT_CONFIG_GLOBAL=/dev/null
export GIT_CONFIG_SYSTEM=/dev/null
export GIT_TERMINAL_PROMPT=0
export GIT_AUTHOR_NAME=local-control-e2e
export GIT_AUTHOR_EMAIL=e2e@local.invalid
export GIT_COMMITTER_NAME=local-control-e2e
export GIT_COMMITTER_EMAIL=e2e@local.invalid

# 1. Workspace: bare remote + seed working repo that writes request envelopes.
WORKSPACE="$(mktemp -d)"
REMOTE="$WORKSPACE/transport.git"
SEED="$WORKSPACE/seed"
CHECKOUT="$WORKSPACE/agent-checkout"
POLICY="$WORKSPACE/policy.json"
STATE_DIR="$WORKSPACE/state"

echo "== local-control e2e loopback"
echo "== workspace: $WORKSPACE"

git init --bare --initial-branch=local-control-bus "$REMOTE" >/dev/null
git clone "$REMOTE" "$SEED" >/dev/null 2>&1 # empty-repo warning expected

seed_head="$(git -C "$SEED" symbolic-ref --short HEAD)"
if [ "$seed_head" != "local-control-bus" ]; then
  git -C "$SEED" checkout -b local-control-bus
fi
git -C "$SEED" config user.name "$GIT_AUTHOR_NAME"
git -C "$SEED" config user.email "$GIT_AUTHOR_EMAIL"

mkdir -p "$SEED/local-control/requests" "$SEED/local-control/receipts"
: > "$SEED/local-control/requests/.gitkeep"
: > "$SEED/local-control/receipts/.gitkeep"
git -C "$SEED" add -A
git -C "$SEED" commit -q -m "seed(local-control): transport branch scaffold"
git -C "$SEED" push -q -u origin local-control-bus

# 2. Request envelope (canonical JSON, request_id == file stem).
REQUEST_ID="e2e-$(date -u +%Y%m%dT%H%M%SZ)"
"$PY" - "$SEED" "$REQUEST_ID" <<'PY'
import json
import pathlib
import sys

seed, request_id = pathlib.Path(sys.argv[1]), sys.argv[2]
envelope = {
    "request_id": request_id,
    "operation": "system.snapshot",
    "machine": {"id": "*"},
    "payload": {},
}
canonical = json.dumps(envelope, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
path = seed / "local-control" / "requests" / f"{request_id}.json"
path.write_text(canonical + "\n", encoding="utf-8")
assert path.stem == request_id
PY
check "request envelope written with id==stem" test -f "$SEED/local-control/requests/$REQUEST_ID.json"
git -C "$SEED" add local-control/requests
git -C "$SEED" commit -q -m "request(local-control): $REQUEST_ID"
git -C "$SEED" push -q origin local-control-bus

# 3. Agent checkout: pre-clone so ensure_checkout() reuses it (never hits GitHub).
git clone -q "$REMOTE" "$CHECKOUT"
git -C "$CHECKOUT" config user.name "$GIT_AUTHOR_NAME"
git -C "$CHECKOUT" config user.email "$GIT_AUTHOR_EMAIL"
check "agent checkout on local-control-bus" test "$(git -C "$CHECKOUT" symbolic-ref --short HEAD)" = "local-control-bus"
check "agent checkout sees the request" test -f "$CHECKOUT/local-control/requests/$REQUEST_ID.json"

# 4. Test policy (no destructive ops; repo is a fake name so any GitHub clone attempt fails loudly).
"$PY" - "$POLICY" "$WORKSPACE" <<'PY'
import json
import pathlib
import sys

policy_path, workspace = pathlib.Path(sys.argv[1]), sys.argv[2]
policy = {
    "machine_id": "*",
    "branch": "local-control-bus",
    "repo": "local/e2e",
    "read_roots": [workspace],
    "write_roots": [],
    "allowed_operations": ["system.snapshot"],
    "allow_destructive": False,
}
policy_path.write_text(json.dumps(policy, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY

# 5. serve --once (run 1) from the worktree root.
serve1_rc=0
(
  cd "$REPO_ROOT" &&
    "$PY" scripts/local_control_agent.py serve \
      --policy "$POLICY" \
      --checkout "$CHECKOUT" \
      --state-dir "$STATE_DIR" \
      --once
) || serve1_rc=$?
check "serve --once (run 1) exit 0" test "$serve1_rc" -eq 0

# 6. Receipt assertions.
RECEIPT="$CHECKOUT/local-control/receipts/$REQUEST_ID.receipt.json"
check "receipt exists in agent checkout" test -f "$RECEIPT"

receipt_ok() {
  "$PY" - "$RECEIPT" "$REQUEST_ID" <<'PY'
import json
import pathlib
import sys

receipt = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
request_id = sys.argv[2]
assert receipt.get("request_id") == request_id, receipt.get("request_id")
assert receipt.get("operation") == "system.snapshot", receipt.get("operation")
assert receipt.get("standing") == "ALIVE", receipt.get("standing")
result = receipt.get("result") or {}
machine_id = result.get("machine_id")
assert isinstance(machine_id, str) and machine_id != "", machine_id
PY
}
check "receipt standing ALIVE + result.machine_id present" receipt_ok

transport_has_receipt() {
  git --git-dir="$REMOTE" ls-tree --name-only "local-control-bus:local-control/receipts" \
    | grep -q "^${REQUEST_ID}\.receipt\.json$"
}
check "receipt committed on transport remote" transport_has_receipt
TIP1="$(git --git-dir="$REMOTE" rev-parse refs/heads/local-control-bus)"

# 7. serve --once (run 2): replay must skip, exactly one receipt, no new commits.
serve2_rc=0
(
  cd "$REPO_ROOT" &&
    "$PY" scripts/local_control_agent.py serve \
      --policy "$POLICY" \
      --checkout "$CHECKOUT" \
      --state-dir "$STATE_DIR" \
      --once
) || serve2_rc=$?
check "serve --once (run 2, replay) exit 0" test "$serve2_rc" -eq 0

exactly_one_receipt() {
  total="$(find "$CHECKOUT/local-control/receipts" -maxdepth 1 -name '*.receipt.json' | wc -l | tr -d ' ')"
  matches="$(find "$CHECKOUT/local-control/receipts" -maxdepth 1 -name "${REQUEST_ID}.receipt.json" | wc -l | tr -d ' ')"
  [ "$total" = "1" ] && [ "$matches" = "1" ]
}
check "replay skip: exactly one receipt for the request" exactly_one_receipt

TIP2="$(git --git-dir="$REMOTE" rev-parse refs/heads/local-control-bus)"
check "transport tip unchanged after replay" test "$TIP1" = "$TIP2"

# 8. Summary. Nothing is cleaned up; the workspace stays for inspection.
echo
echo "== summary: $PASS passed, $FAIL failed"
echo "== workspace preserved: $WORKSPACE"
if [ "$FAIL" -ne 0 ]; then
  exit 1
fi
exit 0
