#!/usr/bin/env bash
# Pre-enrollment preflight for the bounded local-control transport (macOS, arm64).
#
# READ-ONLY probe: installs nothing and mutates nothing outside mktemp dirs,
# except the sanctioned user-space directory probe (mkdir -p then rmdir of the
# leaf dirs this script itself created, checked in check 5).
#
# It verifies exactly what the no-sudo installer
# (scripts/install-local-control-macos-user.sh) will later require:
#   1. Darwin host, non-root user
#   2. python3 (prefers /opt/homebrew/bin/python3, falls back to PATH)
#   3. git
#   4. transport branch reachable on the main checkout's origin (single network touch)
#   5. user-space dirs usable/creatable
#   6. policy validation machinery runs on the example policy
#
# Machine-readable output: one "CHECK <name> PASS|FAIL <detail>" line per check,
# final line "LOCAL_CONTROL_PREFLIGHT=<PASS|FAIL>". Nonzero exit on any FAIL.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

REPO_DIR_EXPLICIT="${REPO_DIR+x}"
REPO_DIR="${REPO_DIR:-/Users/sac/chatgpt-cloud-elixir}"
MAIN_CHECKOUT="${MAIN_CHECKOUT:-/Users/sac/chatgpt-cloud-elixir}"
TRANSPORT_BRANCH="${TRANSPORT_BRANCH:-local-control-bus}"
AGENT_SCRIPT="$SCRIPT_DIR/local_control_agent.py"

# --- output helpers -----------------------------------------------------------

if [[ -t 1 ]] && [[ -z "${NO_COLOR:-}" ]]; then
  C_RED=$'\033[31m'; C_GREEN=$'\033[32m'; C_RESET=$'\033[0m'
else
  C_RED=""; C_GREEN=""; C_RESET=""
fi

PASS_COUNT=0
FAIL_COUNT=0
declare -a FAILED_CHECKS=()

pass() { # pass <name> <detail>
  PASS_COUNT=$((PASS_COUNT + 1))
  printf 'CHECK %s %s%s%s %s\n' "$1" "$C_GREEN" "PASS" "$C_RESET" "$2"
}

fail() { # fail <name> <detail>
  FAIL_COUNT=$((FAIL_COUNT + 1))
  FAILED_CHECKS+=("$1")
  printf 'CHECK %s %s%s%s %s\n' "$1" "$C_RED" "FAIL" "$C_RESET" "$2"
}

# --- scratch ------------------------------------------------------------------

TMPDIR_PREFLIGHT="$(mktemp -d "${TMPDIR:-/tmp}/lc-preflight.XXXXXX")"
trap 'rm -rf "$TMPDIR_PREFLIGHT"' EXIT

# --- check 1: platform + non-root ---------------------------------------------

uname_s="$(uname -s)"
if [[ "$uname_s" == "Darwin" ]]; then
  uid="$(id -u)"
  if [[ "$uid" -ne 0 ]]; then
    pass "platform_nonroot" "Darwin host, uid=$uid (non-root; installer refuses root)"
  else
    fail "platform_nonroot" "uid=0: installer refuses root execution (REFUSED[ROOT_EXECUTION])"
  fi
else
  fail "platform_nonroot" "uname -s=$uname_s (expected Darwin)"
fi

# --- check 2: python3 ----------------------------------------------------------

PYBIN=""
if [[ -x /opt/homebrew/bin/python3 ]]; then
  PYBIN="/opt/homebrew/bin/python3"
elif command -v python3 >/dev/null 2>&1; then
  PYBIN="$(command -v python3)"
fi
if [[ -n "$PYBIN" ]]; then
  py_version="$("$PYBIN" --version 2>&1)"
  pass "python3" "$PYBIN ($py_version)"
else
  fail "python3" "neither /opt/homebrew/bin/python3 nor python3 on PATH"
fi

# --- check 3: git ----------------------------------------------------------------

if command -v git >/dev/null 2>&1; then
  GITBIN="$(command -v git)"
  git_version="$(git --version 2>&1)"
  pass "git" "$GITBIN ($git_version)"
else
  GITBIN=""
  fail "git" "git not found on PATH"
fi

# --- check 4: transport branch reachable on origin (single network touch) -------

if [[ -z "$GITBIN" ]]; then
  fail "transport_branch" "skipped: git missing"
else
  origin_url=""
  if origin_url="$(git -C "$MAIN_CHECKOUT" remote get-url origin 2>&1)"; then
    lsremote_out=""
    if lsremote_out="$(GIT_TERMINAL_PROMPT=0 "$GITBIN" ls-remote "$origin_url" "$TRANSPORT_BRANCH" 2>&1)"; then
      if [[ -n "$lsremote_out" ]]; then
        branch_sha="$(printf '%s' "$lsremote_out" | awk 'NR==1{print $1}')"
        pass "transport_branch" "$origin_url@$TRANSPORT_BRANCH -> ${branch_sha:0:12}"
      else
        fail "transport_branch" "branch $TRANSPORT_BRANCH not present on $origin_url"
      fi
    else
      fail "transport_branch" "git ls-remote failed: ${lsremote_out//$'\n'/ }"
    fi
  else
    fail "transport_branch" "cannot resolve origin of $MAIN_CHECKOUT: ${origin_url//$'\n'/ }"
  fi
fi

# --- check 5: user-space dirs usable/creatable ----------------------------------

USER_DIRS=(
  "$HOME/.local/bin"
  "$HOME/.local/share"
  "$HOME/.local/state"
  "$HOME/.config"
  "$HOME/Library/LaunchAgents"
  "$HOME/Library/Logs"
)
dir_fail=0
dir_detail=""
created_dirs=()
for dir in "${USER_DIRS[@]}"; do
  if [[ -d "$dir" ]]; then
    dir_detail+="${dir#"$HOME"/}:exists "
  elif mkdir -p "$dir" 2>/dev/null; then
    created_dirs+=("$dir")
    dir_detail+="${dir#"$HOME"/}:created "
  else
    dir_fail=1
    dir_detail+="${dir#"$HOME"/}:NOT_CREATABLE "
  fi
done
# Clean up leaves this probe created; leave pre-existing dirs untouched.
for dir in "${created_dirs[@]:-}"; do
  [[ -n "$dir" ]] && rmdir "$dir" 2>/dev/null || true
done
if [[ "$dir_fail" -eq 0 ]]; then
  pass "user_dirs" "$dir_detail"
else
  fail "user_dirs" "$dir_detail"
fi

# --- check 6: policy validation machinery ----------------------------------------

# Resolve the example policy: REPO_DIR (default: main checkout) first; if absent
# there and REPO_DIR was not explicitly set, fall back to this script's own repo
# root (e.g. a wave worktree carrying local-control/ before S03 merges to main).
# The resolution is always recorded in the check detail.
POLICY_EXAMPLE=""
policy_source_desc=""
if [[ -r "$REPO_DIR/local-control/policy.example.json" ]]; then
  POLICY_EXAMPLE="$REPO_DIR/local-control/policy.example.json"
  policy_source_desc="REPO_DIR=$REPO_DIR"
elif [[ -z "$REPO_DIR_EXPLICIT" && -r "$SCRIPT_DIR/../local-control/policy.example.json" ]]; then
  POLICY_EXAMPLE="$(cd "$SCRIPT_DIR/.." && pwd)/local-control/policy.example.json"
  policy_source_desc="script-repo-root fallback (not yet at REPO_DIR=$REPO_DIR)"
fi

if [[ -z "$PYBIN" ]]; then
  fail "policy_validate" "skipped: python3 missing"
elif [[ ! -f "$AGENT_SCRIPT" ]]; then
  fail "policy_validate" "agent script missing: $AGENT_SCRIPT"
elif [[ -z "$POLICY_EXAMPLE" ]]; then
  fail "policy_validate" "example policy missing/unreadable at $REPO_DIR/local-control/policy.example.json (set REPO_DIR)"
else
  policy_copy="$TMPDIR_PREFLIGHT/policy.example.json"
  validate_out=""
  if cp "$POLICY_EXAMPLE" "$policy_copy" 2>/dev/null \
    && validate_out="$("$PYBIN" "$AGENT_SCRIPT" validate-policy --policy "$policy_copy" 2>&1)"; then
    machine_id="$(printf '%s' "$validate_out" | "$PYBIN" -c 'import json,sys; print(json.load(sys.stdin)["machine_id"])' 2>/dev/null || echo "?")"
    pass "policy_validate" "validate-policy exit=0 via $policy_source_desc (machine_id=$machine_id, runner=$PYBIN)"
  else
    validate_rc=$?
    fail "policy_validate" "validate-policy exit=${validate_rc}: ${validate_out:-no output}"
  fi
fi

# --- summary ----------------------------------------------------------------------

echo ""
if [[ "$FAIL_COUNT" -eq 0 ]]; then
  printf '%sLOCAL_CONTROL_PREFLIGHT=PASS%s\n' "$C_GREEN" "$C_RESET"
  echo "checks_passed=$PASS_COUNT checks_failed=0"
  echo "preflight=READ_ONLY agent=$AGENT_SCRIPT policy_example=$POLICY_EXAMPLE"
  exit 0
else
  printf '%sLOCAL_CONTROL_PREFLIGHT=FAIL%s\n' "$C_RED" "$C_RESET"
  echo "checks_passed=$PASS_COUNT checks_failed=$FAIL_COUNT failed=${FAILED_CHECKS[*]}"
  exit 1
fi
