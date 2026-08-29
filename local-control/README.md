# ChatGPT Local Computer Control

This subtree adds a **bounded local-actuation transport** to `chatgpt-cloud-elixir`.

The purpose is to let an authorized ChatGPT session manufacture a typed request in GitHub, have a user-controlled local agent execute that request on a specific enrolled computer, and return an evidence-bearing receipt.

```text
ChatGPT / scheduled cell
        |
        | connected GitHub CRUD
        v
local-control-bus:local-control/requests/<request-id>.json
        |
        | local agent polls exact branch
        v
scripts/local_control_agent.py
        |
        | local policy admission
        v
filesystem / allowlisted process / bounded macOS action
        |
        | typed result + replay ledger
        v
local-control-bus:local-control/receipts/<request-id>.receipt.json
        |
        v
ChatGPT reads exact receipt
```

The **local machine remains the authority boundary**. GitHub transports intents and receipts; it does not grant ambient execution rights.

## Why not a self-hosted GitHub Actions runner?

A self-hosted runner makes repository workflow code equivalent to arbitrary host code execution. That is useful in some controlled environments, but it collapses `SELECT`, `CONSTRUCT`, and `DO` and makes every workflow-editing principal part of the local machine's execution authority.

This implementation instead admits each requested operation through a local policy. The default protocol deliberately exposes **no raw shell string**.

## Transport branch

Use the persistent branch:

```text
local-control-bus
```

Requests and receipts are transport/evidence and should remain off ordinary feature diffs.

A request filename is part of its identity:

```text
local-control/requests/<request-id>.json
```

The JSON `request_id` must exactly equal `<request-id>`. A completed request produces:

```text
local-control/receipts/<request-id>.receipt.json
```

The local replay ledger independently remembers executed request IDs so deleting a GitHub receipt does not silently authorize replay.

## Request envelope

```json
{
  "request_id": "20260825T081000Z-my-mac-status",
  "operation": "system.snapshot",
  "machine": {"id": "sean-mac"},
  "expires_at": "2026-08-25T08:20:00Z",
  "payload": {}
}
```

`machine.id` must be the machine's configured stable ID or `*`. Prefer a specific ID for consequential work. `expires_at` is strongly recommended for every request.

Do not put credentials, API keys, cookies, private tokens, or other secrets in requests. This repository is public and request files are Git history.

## Bounded operations

The agent implements these operation types. The local policy can disable any of them.

| Operation | Effect | Primary fence |
| --- | --- | --- |
| `system.snapshot` | Return machine/platform identity | machine scope |
| `filesystem.list` | List one directory | `read_roots` |
| `filesystem.read` | Read UTF-8/binary-as-text with digest/truncation | `read_roots` + output cap |
| `filesystem.write` | Atomic UTF-8 file replacement | `write_roots` |
| `filesystem.mkdir` | Create a directory | `write_roots` |
| `filesystem.delete` | Delete file/directory | `write_roots` + `allow_destructive=true` |
| `process.run` | Execute argv without `shell=True` | `allowed_executables` + cwd root + timeout |
| `macos.open` | Open an allowed app/path/optional URL | app/root/URL policy |
| `macos.notify` | Display a local notification | macOS-only bounded implementation |
| `macos.applescript.named` | Execute a locally predefined script by ID | script body exists only in local policy |

There is intentionally no `shell.exec`, no arbitrary AppleScript request body, no remote environment-variable injection, and no request-level ability to widen policy.

## Local policy

Start from `local-control/policy.example.json`, but keep the active policy **outside the repository**:

```bash
mkdir -p ~/.config/chatgpt-local-control
cp local-control/policy.example.json ~/.config/chatgpt-local-control/policy.json
$EDITOR ~/.config/chatgpt-local-control/policy.json
python3 scripts/local_control_agent.py validate-policy \
  --policy ~/.config/chatgpt-local-control/policy.json
```

The policy owns:

- machine ID;
- exact repo and transport branch;
- allowed operations;
- readable/writable filesystem roots;
- executable allowlist;
- allowed macOS applications;
- optional URL opening;
- destructive-operation permission;
- timeout and output ceilings;
- locally defined named AppleScripts.

A request cannot mutate the policy.

## Git authentication

The isolated transport checkout must be able to fetch requests and push receipts. If the local machine already uses GitHub CLI authentication:

```bash
gh auth status
gh auth setup-git
```

The agent does not read or copy the GitHub token into a receipt. Git handles transport authentication normally.

## One-shot qualification

After the `local-control-bus` branch exists and the policy is configured:

```bash
python3 scripts/local_control_agent.py serve \
  --policy ~/.config/chatgpt-local-control/policy.json \
  --checkout ~/.local/share/chatgpt-local-control/repo \
  --state-dir ~/.local/state/chatgpt-local-control \
  --once
```

The agent creates its own isolated checkout if absent. It never uses an unrelated working repository as its transport checkout.

## Continuous service

Run the same command without `--once`:

```bash
python3 scripts/local_control_agent.py serve \
  --policy ~/.config/chatgpt-local-control/policy.json \
  --checkout ~/.local/share/chatgpt-local-control/repo \
  --state-dir ~/.local/state/chatgpt-local-control \
  --poll-seconds 15
```

Stopping that process removes ChatGPT's local actuation channel. There is no inbound listener and no port exposed on the local machine; the agent only performs outbound Git fetch/push operations.

## Examples

### Inspect the machine

```json
{
  "request_id": "20260825T081000Z-sean-mac-snapshot",
  "operation": "system.snapshot",
  "machine": {"id": "sean-mac"},
  "expires_at": "2026-08-25T08:15:00Z",
  "payload": {}
}
```

### Run an admitted command

```json
{
  "request_id": "20260825T081100Z-git-status",
  "operation": "process.run",
  "machine": {"id": "sean-mac"},
  "expires_at": "2026-08-25T08:20:00Z",
  "payload": {
    "argv": ["git", "status", "--short"],
    "cwd": "~/Projects/example",
    "timeout_seconds": 30
  }
}
```

`argv` is passed directly to an admitted executable with `shell=False`; shell operators, interpolation, redirection, and command substitution are not interpreted.

### Open an admitted macOS app

```json
{
  "request_id": "20260825T081200Z-open-terminal",
  "operation": "macos.open",
  "machine": {"id": "sean-mac"},
  "expires_at": "2026-08-25T08:20:00Z",
  "payload": {"mode": "app", "value": "Terminal"}
}
```

### Execute a locally admitted GUI macro

The repository request contains only the stable name:

```json
{
  "request_id": "20260825T081300Z-finder-front",
  "operation": "macos.applescript.named",
  "machine": {"id": "sean-mac"},
  "expires_at": "2026-08-25T08:20:00Z",
  "payload": {"script_id": "finder.front"}
}
```

The actual AppleScript is defined in the local policy and therefore cannot be replaced by a remote request.

## Receipts and standing

Every local request produces an operation-level receipt containing:

- request ID and SHA-256;
- operation;
- machine ID;
- repo/branch transport identity;
- start/end timestamps;
- result or typed refusal/error;
- exact standing.

Standing semantics:

- `ALIVE` — the exact admitted operation executed on the target machine and a receipt was persisted.
- `REFUSED` — local policy, machine scope, expiry, replay, path, executable, or platform law rejected the request.
- `BUILD_BROKEN` — the admitted operation reached execution machinery but the executor violated/failed its contract, including timeout or unexpected runtime errors.
- `UNKNOWN` — receipt evidence is unavailable.

An Actions status or Git commit alone is not local execution proof; the local operation receipt is the evidence.

## DfCM use

This surface turns a local computer into another bounded manufacturing/observation node:

```text
Project #2 memory
      +
GitHub repository evidence
      +
local machine observations
      ↓
DfCM frontier
      ↓
local-control intent
      ↓
local admitted actuation
      ↓
receipt
      ↓
Project #2 memory / next frontier
```

Use it to **expand lawful capability**, not to erase authority distinctions. A repeated useful local sequence should become a named, locally admitted reusable operation or generator rather than an ever-growing arbitrary command stream.

## Revocation

Local authority is intentionally easy to revoke:

1. stop the local agent;
2. remove or narrow the local policy;
3. revoke local Git credentials if needed;
4. archive/delete pending transport requests;
5. preserve receipts/replay state for audit.

No cloud-side change can restart a stopped local agent by itself.
