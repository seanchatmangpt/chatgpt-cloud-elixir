# Track B: approval-gated Colima capsule runner

This is intentionally **not** "give ChatGPT Colima." It is one bounded bridge for one observed gap: run this repository's Linux-assuming capsule build/verify scripts inside the user's existing Colima VM, with mandatory local human approval.

## Remote request surface

Only this shape is admitted:

```json
{
  "request_id": "20260826T060000Z-build-process-intelligence",
  "operation": "process.run",
  "machine": {"id": "sean-mac"},
  "expires_at": "2026-08-26T06:20:00Z",
  "payload": {
    "script": "scripts/build-process-intelligence.sh",
    "timeout_seconds": 1200
  }
}
```

`payload.script` must match `scripts/build-*.sh` or `scripts/verify-*.sh` and resolve to a real file inside the locally configured `repo_root`. There is no remote argv, arbitrary command string, environment injection, filesystem operation, GUI operation, Docker operation, or Kubernetes operation.

The local agent manufactures a command equivalent to:

```text
colima ssh -- bash -lc 'cd -- <locally-configured-repo-root> && exec bash ./scripts/build-process-intelligence.sh'
```

The request cannot supply or alter the shell text.

## Approval lifecycle

1. ChatGPT writes a request to `local-control-bus:local-control/requests/<id>.json`.
2. The local agent validates machine, expiry, operation, script path, repository identity, platform, and Colima availability.
3. The agent writes `local-control/receipts/<id>.receipt.json` with `standing=PENDING_APPROVAL`, the exact request SHA-256, and `command.literal_command`.
4. macOS receives a best-effort notification.
5. The human runs:

```bash
python3 scripts/local_control_agent.py approve <id> \
  --policy ~/.config/chatgpt-local-control/policy.json
```

The CLI syncs the request, prints the literal command and request hash, and asks for confirmation. Approval is stored only under `~/.local/state/chatgpt-local-control/approvals/` and is bound to that exact request hash.
6. On the next poll, the agent executes only that approved command and replaces the pending receipt with `ALIVE` or `BUILD_BROKEN`. A denied request becomes `REFUSED[LOCAL_APPROVAL_DENIED]`.

No request auto-runs.

## Local policy

Copy `local-control/policy.example.json` outside the repository and set at least `machine_id` and `repo_root`:

```bash
mkdir -p ~/.config/chatgpt-local-control
cp local-control/policy.example.json ~/.config/chatgpt-local-control/policy.json
$EDITOR ~/.config/chatgpt-local-control/policy.json
python3 scripts/local_control_agent.py validate-policy \
  --policy ~/.config/chatgpt-local-control/policy.json
```

The transport checkout is isolated from the working repository:

```bash
python3 scripts/local_control_agent.py serve \
  --policy ~/.config/chatgpt-local-control/policy.json \
  --checkout ~/.local/share/chatgpt-local-control/repo \
  --state-dir ~/.local/state/chatgpt-local-control
```

Stopping this process revokes the bridge. It opens no inbound listener; it uses outbound Git fetch/push only.

## Evidence

A successful terminal receipt contains the exact command, repository HEAD/dirty state, script SHA-256, exit code, stdout/stderr, output byte counts and SHA-256 digests, truncation flags, duration, and `standing=ALIVE`. Exit zero without that operation-level receipt is not the crown.

## Deliberate exclusion

`kind` is phase two at earliest. No observed blocker in the motivating session requires a local Kubernetes cluster, so Kubernetes access is not admitted here.
