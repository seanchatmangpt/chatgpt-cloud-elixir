# Local control — bounded ChatGPT-to-laptop actuation

This subtree is the operator-facing entry point for the **bounded local-control transport**
in `chatgpt-cloud-elixir`. An authorized ephemeral ChatGPT cloud instance files a typed
request on a Git branch; a user-owned agent on the enrolled laptop admits that request
against a local policy; only what the policy admits executes; a typed receipt is pushed
back for the cloud instance to read.

```text
ChatGPT (ephemeral cloud instance) → local-control-bus request → local agent → policy admission → bounded host operation → typed receipt → ChatGPT
```

The laptop remains the authority boundary. Git transports intents and evidence; it grants
no ambient execution rights. Companion docs: `local-control/AGENTS.md` (agent contract)
and `local-control/NO_SUDO.md` (installer law).

## Transport layout

Everything moves over one persistent branch:

- Transport branch: `local-control-bus` (requests and receipts stay off ordinary feature diffs)
- Requests: `local-control/requests/<request_id>.json`
- Receipts: `local-control/receipts/<request_id>.receipt.json`
- Schemas: `local-control/request.schema.json` and `local-control/receipt.schema.json`

The filename is part of the authority: the JSON `request_id` must equal the file stem
`<request_id>`, or the request is refused with `REQUEST_ID_PATH_MISMATCH`. A local replay
ledger (`<state-dir>/executed.json`) independently remembers every executed request ID, so
deleting a receipt from Git cannot authorize replay (`REPLAY_DETECTED`).

Request envelope (full contract in `request.schema.json`):

```json
{
  "request_id": "20260923T120000Z-my-mac-snapshot",
  "operation": "system.snapshot",
  "machine": {"id": "<hostname>"},
  "expires_at": "2026-09-23T12:15:00Z",
  "payload": {}
}
```

`machine.id` must be this machine's configured ID or `*`; prefer the specific ID.
`expires_at` (UTC ISO with timezone) is strongly recommended. Never put credentials,
tokens, or secrets in a request — request files are Git history in a public repository.

## Authority boundary

- The **active policy lives outside Git**, installed at
  `~/.config/chatgpt-local-control/policy.json` on enrolled machines.
  Git carries `local-control/policy.example.json` only.
- **Remote requests cannot widen policy.** There is no request field that mutates policy,
  injects environment variables, carries arbitrary AppleScript text, or bypasses
  replay/expiry/machine scope. The policy alone owns: machine ID, repo and transport
  branch, allowed operations, read/write filesystem roots, executable and app allowlists,
  URL-opening and destructive-operation permissions, timeout/output ceilings, and locally
  defined named AppleScripts.
- **No inbound listener.** The agent performs outbound `git fetch` / `git push` only;
  nothing listens on any local port.
- **Stopping the agent revokes the actuation path.** No cloud-side change can restart a
  stopped local agent by itself.

## Enrollment runbook (macOS laptop)

### 1. Preflight

```bash
bash scripts/local_control_enroll_preflight.sh
```

Checks `python3`, git reachability of the transport branch, launchd user paths, and
policy validation. Fix anything it reports before continuing.

### 2. Install (never with sudo; root is refused)

```bash
bash scripts/install-local-control-macos-user.sh
```

The installer deliberately refuses execution as UID 0 (`REFUSED[ROOT_EXECUTION]`) — do
**not** prefix it with `sudo`. It also refuses non-Darwin hosts and any path override
that escapes `$HOME` (`REFUSED[NON_USERSPACE_PATH]`). It requires `git`, `gh`,
`python3`, `launchctl` on PATH, runs `gh auth status` / `gh auth setup-git`, clones a
single-branch `local-control-bus` checkout, seeds the active policy from the example
(mode `0600`) if absent, validates it, and registers the service in the **per-user
launchd domain only** (`gui/<uid>/com.openai.chatgpt-local-control`) — no LaunchDaemon,
no privileged helper, no root-owned file.

### 3. What the LaunchAgent does

The service runs, with `KeepAlive`:

```bash
python3 scripts/local_control_agent.py serve \
  --policy ~/.config/chatgpt-local-control/policy.json \
  --checkout ~/.local/share/chatgpt-local-control/repo \
  --state-dir ~/.local/state/chatgpt-local-control \
  --poll-seconds 15
```

It polls `local-control-bus` **every 15 seconds**, executes newly admitted requests, and
pushes receipts. The isolated transport checkout lives at
`~/.local/share/chatgpt-local-control/repo`; replay/state evidence at
`~/.local/state/chatgpt-local-control`; logs at `~/Library/Logs/chatgpt-local-control/`.

Inspect:

```bash
launchctl print gui/$(id -u)/com.openai.chatgpt-local-control
tail -f ~/Library/Logs/chatgpt-local-control/stderr.log
```

### 4. Validate the policy

```bash
python3 scripts/local_control_agent.py validate-policy \
  --policy ~/.config/chatgpt-local-control/policy.json
```

Prints the resolved machine ID, allowed operations, roots, and executables. Edit the
policy as the local user (machine ID, roots, executables, apps, named AppleScripts)
before consequential actuation.

A no-install trial is possible without launchd: run the same `serve` command with
`--once` for a single poll/execute cycle.

### 5. Revoke

```bash
bash scripts/uninstall-local-control-macos-user.sh
```

Stops the agent and removes its plist. Policy, transport checkout, replay ledger, logs,
and receipts are preserved for audit and can be deleted later as the local user.
Immediate stop without the uninstaller:

```bash
launchctl bootout gui/$(id -u)/com.openai.chatgpt-local-control
```

## Filing requests (for ephemeral cloud instances)

Point cloud instances at `local-control/CLOUD-INSTANCE-GUIDE.md` — it carries the exact
git-only commands and the envelope cheat sheet. Canonical tools:

- `scripts/local_control_request.py` — CLI to file, list, and fetch requests and receipts
- `scripts/local_control_e2e_loopback.sh` — no-network loopback proof (temporary bare
  transport → request → agent `--once` → receipt → replay skip)

## Bounded operations

The agent implements these operation types; the local policy can disable any of them.

| Operation | Effect | Primary fence |
| --- | --- | --- |
| `system.snapshot` | Return machine/platform identity | machine scope |
| `filesystem.list` | List one directory | `read_roots` |
| `filesystem.read` | Read with digest/truncation | `read_roots` + output cap |
| `filesystem.write` | Atomic UTF-8 file replacement | `write_roots` |
| `filesystem.mkdir` | Create a directory | `write_roots` |
| `filesystem.delete` | Delete file/directory | `write_roots` + `allow_destructive=true` |
| `process.run` | Execute argv with `shell=False` | `allowed_executables` + cwd root + timeout |
| `macos.open` | Open an allowed app/path/optional URL | app/root/URL policy |
| `macos.notify` | Display a local notification | macOS-only bounded implementation |
| `macos.applescript.named` | Run a locally predefined script by ID | script body exists only in local policy |

There is intentionally no `shell.exec`: `process.run` passes `argv` directly to an
allowlisted executable with no shell interpretation of operators, interpolation,
redirection, or substitution.

**Refusal-first stance.** A request that cannot be fully admitted produces a typed
`REFUSED` receipt — never a partial execution. Refusal is a successful safety outcome.
Common refusal reasons: `OPERATION_NOT_ALLOWED`, `MACHINE_SCOPE_VIOLATION`,
`REQUEST_EXPIRED`, `REPLAY_DETECTED`, `READ_PATH_NOT_ALLOWED`, `WRITE_PATH_NOT_ALLOWED`,
`EXECUTABLE_NOT_ALLOWED`, `DESTRUCTIVE_OPERATION_DISABLED`, `REQUEST_ID_PATH_MISMATCH`.

## Receipts and standing

Every processed request produces a receipt (schema: `local-control/receipt.schema.json`)
binding receipt version, request ID and SHA-256, operation, machine ID, transport
repo/branch, start/end timestamps, result or typed refusal, and standing:

- `ALIVE` — the exact admitted operation executed on this machine and the receipt was persisted.
- `REFUSED` — local admission law rejected the request (policy, machine scope, expiry,
  replay, path, executable, or platform). Nothing executed.
- `BUILD_BROKEN` — the admitted operation reached execution machinery but violated its
  contract (timeout or unexpected runtime error).

(`UNKNOWN` also appears in the receipt schema for evidence-unavailable cases.)

A Git commit or a CI status is not local execution proof; the local operation receipt is.

## Verification

Courts are stdlib `unittest` (no pytest):

```bash
python3 -m unittest discover -s tests -p 'test_local_control*.py'
```

On this laptop the pinned runner is `/opt/homebrew/bin/python3`; the agent stays
compatible with system `python3` 3.9. The loopback proof is:

```bash
bash scripts/local_control_e2e_loopback.sh
```

CI (`.github/workflows/local-control-ci.yml`, ubuntu-24.04, Python 3.12) covers:

- `py_compile` of `scripts/local_control_agent.py`;
- `bash -n` parse of all four install/uninstall scripts;
- `tests/test_local_control_agent.py` — admission fences: machine scope, read/write root
  fencing, destructive-off, executable allowlist, no-shell argv execution, expiry,
  replay, and request-ID/filename binding;
- `tests/test_local_control_no_sudo.py` — the no-sudo user installer contract (no sudo
  invocation, user-scoped paths, root refusal, `$HOME` containment);
- `validate-policy` on `local-control/policy.example.json`.

Hosted CI supplements consumer execution; it does not replace it. `ALIVE` for this
capability requires execution on the enrolled machine itself.

## Use

This surface turns the laptop into one bounded manufacturing/observation node. Use it to
expand lawful capability, not to erase authority distinctions: a repeated useful local
sequence should become a named, locally admitted bounded operation rather than an
ever-growing arbitrary command stream. The agent contract in `local-control/AGENTS.md`
governs changes to this subtree.
