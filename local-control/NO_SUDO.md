# No-sudo macOS installation

The local-control agent can run entirely in the logged-in user's macOS session. Root authority is neither required nor admitted by the explicit user-space installer.

## Install

From a checkout containing the local-control feature:

```bash
bash scripts/install-local-control-macos-user.sh
```

The installer deliberately refuses execution as UID 0. Do **not** prefix it with `sudo`.

It uses only user-owned locations:

```text
~/.local/share/chatgpt-local-control/      isolated transport checkout
~/.config/chatgpt-local-control/           active local policy
~/.local/state/chatgpt-local-control/      replay/state evidence
~/Library/LaunchAgents/                    per-user launchd registration
~/Library/Logs/chatgpt-local-control/      local agent logs
```

The service is registered only in the per-user launchd domain:

```text
gui/<uid>/com.openai.chatgpt-local-control
```

It does not install a LaunchDaemon, privileged helper, system extension, kernel extension, `/usr/local` binary, `/Library` service, or root-owned file.

## Preconditions

The user account needs these ordinary commands available in its PATH:

```text
git
gh
python3
launchctl
```

The GitHub CLI must already be authenticated for the account/repository transport:

```bash
gh auth status
gh auth setup-git
```

No GitHub credential is copied into the policy or receipts. Git handles transport authentication through the user's existing credential configuration.

## Policy

On first install the script creates:

```text
~/.config/chatgpt-local-control/policy.json
```

from the repository example and sets mode `0600`. Edit that file as the local user before consequential actuation. Remote requests cannot widen this policy.

Any installer path override must resolve beneath the current user's `$HOME`; attempts to redirect the user installer to system locations are refused as `REFUSED[NON_USERSPACE_PATH]`.

## Inspect

```bash
launchctl print gui/$(id -u)/com.openai.chatgpt-local-control
tail -f ~/Library/Logs/chatgpt-local-control/stderr.log
```

## Revoke without sudo

```bash
bash scripts/uninstall-local-control-macos-user.sh
```

or immediately stop the service with:

```bash
launchctl bootout gui/$(id -u)/com.openai.chatgpt-local-control
```

The uninstaller preserves policy, receipts, replay ledger, logs, and transport state for audit/recovery. Those can be deleted later as the local user if intentionally desired.

## Standing

Successful installation proves only that the same-user service was registered. Local actuation is `ALIVE` only after an exact admitted request executes on the enrolled machine and its typed receipt is persisted back through the transport.
