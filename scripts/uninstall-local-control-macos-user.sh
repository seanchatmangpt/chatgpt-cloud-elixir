#!/usr/bin/env bash
set -euo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "REFUSED[UNSUPPORTED_PLATFORM]: macOS uninstaller requires Darwin" >&2
  exit 2
fi

if [[ "$(id -u)" -eq 0 ]]; then
  echo "REFUSED[ROOT_EXECUTION]: run this uninstaller as the enrolled macOS user; sudo is neither required nor admitted" >&2
  exit 2
fi

label="com.openai.chatgpt-local-control"
plist="$HOME/Library/LaunchAgents/$label.plist"
uid="$(id -u)"

launchctl bootout "gui/$uid/$label" >/dev/null 2>&1 || true
rm -f "$plist"

cat <<EOF
ALIVE[LOCAL_CONTROL_USER_SERVICE_REVOKED]
privilege=same-user-no-sudo
label=$label

The per-user LaunchAgent is stopped and its plist removed.
Persistent policy, transport checkout, replay ledger, logs, requests, and receipts are intentionally preserved for audit/recovery.
EOF
