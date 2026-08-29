#!/usr/bin/env bash
set -euo pipefail

# Explicit user-space installer for ChatGPT local control on macOS.
# This installer intentionally refuses root execution and never writes outside
# the invoking user's home directory.

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "REFUSED[UNSUPPORTED_PLATFORM]: macOS installer requires Darwin" >&2
  exit 2
fi

if [[ "$(id -u)" -eq 0 ]]; then
  echo "REFUSED[ROOT_EXECUTION]: run this installer as your normal macOS user; sudo is neither required nor admitted" >&2
  exit 2
fi

repo="${CHATGPT_LOCAL_CONTROL_REPO:-seanchatmangpt/chatgpt-cloud-elixir}"
branch="${CHATGPT_LOCAL_CONTROL_BRANCH:-local-control-bus}"
base="${CHATGPT_LOCAL_CONTROL_HOME:-$HOME/.local/share/chatgpt-local-control}"
checkout="$base/repo"
config_dir="${CHATGPT_LOCAL_CONTROL_CONFIG_DIR:-$HOME/.config/chatgpt-local-control}"
state_dir="${CHATGPT_LOCAL_CONTROL_STATE_DIR:-$HOME/.local/state/chatgpt-local-control}"
policy="$config_dir/policy.json"
label="com.openai.chatgpt-local-control"
launch_agents="$HOME/Library/LaunchAgents"
plist="$launch_agents/$label.plist"
log_dir="$HOME/Library/Logs/chatgpt-local-control"

# Fail closed if an override attempts to escape the user home directory.
python3 - "$HOME" "$base" "$config_dir" "$state_dir" "$launch_agents" "$log_dir" <<'PY'
from pathlib import Path
import sys
home = Path(sys.argv[1]).expanduser().resolve()
for raw in sys.argv[2:]:
    path = Path(raw).expanduser().resolve()
    try:
        path.relative_to(home)
    except ValueError:
        raise SystemExit(f"REFUSED[NON_USERSPACE_PATH]: {path} is outside {home}")
PY

for cmd in git gh python3 launchctl; do
  command -v "$cmd" >/dev/null 2>&1 || {
    echo "BLOCKED[MISSING_EXECUTABLE]: $cmd" >&2
    exit 3
  }
done

gh auth status >/dev/null
gh auth setup-git >/dev/null

mkdir -p "$base" "$config_dir" "$state_dir" "$log_dir" "$launch_agents"

if [[ ! -d "$checkout/.git" ]]; then
  git clone --single-branch --branch "$branch" "https://github.com/$repo.git" "$checkout"
else
  git -C "$checkout" fetch origin "$branch"
  git -C "$checkout" checkout "$branch"
  git -C "$checkout" reset --hard "origin/$branch"
fi

agent_py="$checkout/scripts/local_control_agent.py"
if ! grep -q "class ApprovalStore" "$agent_py" 2>/dev/null || ! grep -q "def requires_approval" "$agent_py" 2>/dev/null; then
  echo "REFUSED[MISSING_APPROVAL_GATE]: $agent_py (branch '$branch') has no ApprovalStore/requires_approval -- installing it would run every admitted operation with zero local human confirmation, contradicting local-control/AGENTS.md's Requirement 9. This branch is stale relative to the mandatory approval-gate feature. Sync '$branch' from a ref that has the gate, or set CHATGPT_LOCAL_CONTROL_BRANCH to one that does, then re-run this installer." >&2
  exit 4
fi

if [[ ! -f "$policy" ]]; then
  cp "$checkout/local-control/policy.example.json" "$policy"
  chmod 600 "$policy"
  echo "Created $policy from the example policy." >&2
  echo "Edit machine_id, roots, executables, apps, and optional named AppleScripts before consequential actuation." >&2
fi

python3 "$checkout/scripts/local_control_agent.py" validate-policy --policy "$policy"

python_path="$(command -v python3)"
cat >"$plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$label</string>
  <key>ProgramArguments</key>
  <array>
    <string>$python_path</string>
    <string>$checkout/scripts/local_control_agent.py</string>
    <string>serve</string>
    <string>--policy</string>
    <string>$policy</string>
    <string>--checkout</string>
    <string>$checkout</string>
    <string>--state-dir</string>
    <string>$state_dir</string>
    <string>--poll-seconds</string>
    <string>15</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>$log_dir/stdout.log</string>
  <key>StandardErrorPath</key>
  <string>$log_dir/stderr.log</string>
  <key>ProcessType</key>
  <string>Background</string>
</dict>
</plist>
PLIST
chmod 600 "$plist"

# Per-user launchd domain only. No LaunchDaemon and no sudo.
uid="$(id -u)"
launchctl bootout "gui/$uid/$label" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$uid" "$plist"
launchctl kickstart -k "gui/$uid/$label"

cat <<EOF
ALIVE[LOCAL_CONTROL_USER_SERVICE_INSTALLED]
privilege=same-user-no-sudo
label=$label
repo=$repo
branch=$branch
checkout=$checkout
policy=$policy
state_dir=$state_dir
plist=$plist
logs=$log_dir

Inspect:
  launchctl print gui/$uid/$label
  tail -f '$log_dir/stderr.log'

Revoke immediately (also no sudo):
  launchctl bootout gui/$uid/$label
EOF
