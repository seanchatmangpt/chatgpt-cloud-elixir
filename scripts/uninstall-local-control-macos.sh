#!/usr/bin/env bash
set -euo pipefail

label="com.openai.chatgpt-local-control"
plist="$HOME/Library/LaunchAgents/$label.plist"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "REFUSED[UNSUPPORTED_PLATFORM]: macOS uninstaller requires Darwin" >&2
  exit 2
fi

launchctl bootout "gui/$(id -u)/$label" >/dev/null 2>&1 || true
rm -f "$plist"

cat <<'EOF'
ALIVE[LOCAL_CONTROL_SERVICE_REVOKED]
The launch agent is stopped and its plist removed.

Persistent policy, transport checkout, replay ledger, logs, requests, and receipts are intentionally preserved for audit/recovery. Remove them manually only if you intentionally want to destroy that evidence/state.
EOF
