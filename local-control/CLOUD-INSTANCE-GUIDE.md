# Cloud instance guide: bounded local control

You are an ephemeral ChatGPT cloud instance (restricted container: `git`/`gh` to GitHub
works; no inbound network, no direct access to the operator's laptop). This is the exact
procedure to have the operator's laptop perform one bounded operation and to read back the
typed receipt.

Model of the transport:

```text
you (cloud) --git/gh--> local-control-bus:local-control/requests/<request_id>.json
laptop agent (polls outbound) --local policy admission--> executes ONE bounded operation
laptop agent --git push--> local-control-bus:local-control/receipts/<request_id>.receipt.json
you (cloud) --git/gh--> read the receipt
```

Repo: `seanchatmangpt/chatgpt-cloud-elixir`. Transport branch: `local-control-bus`.
The laptop is the authority boundary. GitHub carries intents and receipts only.

## 1. Law (read before filing anything)

- Policy cannot be widened from the cloud side. Allowed operations, readable/writable
  roots, executable allowlist, apps, named AppleScripts, timeouts and caps all live in the
  laptop's local policy, outside Git. A request cannot mutate any of it.
- A `REFUSED` receipt is a successful safety outcome. Do not retry a refusal with cosmetic
  changes; re-derive the request so it fits the policy, or stop.
- Never re-file an identical `request_id`. The agent keeps a replay ledger outside Git, so
  a replayed id is refused (`REPLAY_DETECTED`) even if the old receipt was deleted from the
  branch. If a receipt already exists for an id, the agent skips the file entirely. Always
  mint a fresh, unique id (timestamp in the id makes this natural).
- One request per file. Two operations = two files (two commits is fine).
- Keep payloads small. Output is capped (`max_output_bytes`, default 100000) and a request
  body is Git history in a public repo: never put credentials, tokens, cookies, or secrets
  in a request.
- Add-only discipline: do not modify or delete other participants' requests or receipts on
  the bus, and never force-push the transport branch.

## 2. Get the transport branch

Route A — plain git (clone only the bus branch):

```bash
REPO=seanchatmangpt/chatgpt-cloud-elixir
BRANCH=local-control-bus
git clone --single-branch --branch "$BRANCH" "https://github.com/${REPO}.git" lc-bus
cd lc-bus
```

If you already have a clone of the repo on another branch, do not switch your worktree;
fetch the bus branch and read objects from it directly:

```bash
git clone --no-checkout https://github.com/seanchatmangpt/chatgpt-cloud-elixir.git lc-meta
cd lc-meta
git fetch origin local-control-bus
git show "FETCH_HEAD:local-control/README.md"        # transport contract
git show "FETCH_HEAD:local-control/request.schema.json"
```

Route B — GitHub CLI only (no local checkout needed for filing/reading; see sections 4
and 5):

```bash
gh auth status   # must already be authenticated in the container
```

## 3. Discover the machine id

`machine.id` must be either `"*"` (wildcard) or the laptop's exact configured id. You
normally do not know the hostname. Discover it by filing a `system.snapshot` request with
`machine.id: "*"` and reading `machine_id` / `result.machine_id` / `result.hostname` from
the receipt. (You can also just ask the operator.) Use `"*"` only for this discovery — for
anything else target the exact id, because `"*"` fans out to every enrolled machine.

## 4. File a request

### 4.1 Filename convention

```text
local-control/requests/<instance>-<yyyymmddThhmmssZ>-<short-op>.json
```

- `<request_id>` (the file stem, without `.json`) must exactly equal the JSON
  `request_id` field. Mismatch = `REQUEST_ID_PATH_MISMATCH` refusal.
- Allowed id characters: `A-Z a-z 0-9 . _ : -` (no `/`, no spaces), max length 200.
- Example stem: `ccx1-20260923T120000Z-snapshot`.

```bash
REPO=seanchatmangpt/chatgpt-cloud-elixir
BRANCH=local-control-bus
INSTANCE=ccx1                                           # your instance name
TS=$(date -u +%Y%m%dT%H%M%SZ)
OP=snapshot                                             # short op label
REQ_ID="${INSTANCE}-${TS}-${OP}"
REQ_PATH="local-control/requests/${REQ_ID}.json"
```

### 4.2 Envelope cheat sheet

Schema: `local-control/request.schema.json`. Required fields:
`request_id`, `operation`, `machine`, `payload`. No extra fields beyond this table.

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `request_id` | string | yes | 1–200 chars, `^[A-Za-z0-9._:-]+$`; must equal the filename stem |
| `operation` | string | yes | one of the 10 operations below |
| `machine` | object | yes | exactly `{"id": ...}`; `id` is `"*"` or the exact laptop id (1–200 chars) |
| `expires_at` | string | no (strongly recommended) | UTC ISO 8601 **with timezone**: `2026-09-23T12:10:00Z` or `...+00:00`; no fractional seconds. Recommended: now + 10 minutes. Expired = `REQUEST_EXPIRED`; a timezone-less value yields `BUILD_BROKEN` (`ValueError`) |
| `payload` | object | yes | operation-specific; see 4.3. Use `{}` for `system.snapshot` |

Minimal envelope:

```json
{
  "request_id": "ccx1-20260923T120000Z-snapshot",
  "operation": "system.snapshot",
  "machine": {"id": "*"},
  "expires_at": "2026-09-23T12:10:00Z",
  "payload": {}
}
```

### 4.3 Payload keys per operation

Paths accept `~` and `$VAR` expansion. "Required" means: omit it and the request fails
(`BUILD_BROKEN`, reason `KeyError`, unless marked otherwise).

| Operation | Key | Required | Meaning |
| --- | --- | --- | --- |
| `system.snapshot` | — | — | payload is ignored; use `{}` |
| `filesystem.list` | `path` | yes | directory to list (must be inside policy `read_roots`) |
| `filesystem.read` | `path` | yes | file to read (inside `read_roots`) |
| | `max_bytes` | no | clamp on returned bytes; further capped by policy (default cap 100000) |
| `filesystem.write` | `path` | yes | file to atomically replace (inside `write_roots`) |
| | `content` | no | UTF-8 text; default `""` |
| `filesystem.mkdir` | `path` | yes | directory to create (inside `write_roots`) |
| | `parents` | no | default `true` |
| | `exist_ok` | no | default `true` |
| `filesystem.delete` | `path` | yes | file/dir to delete (inside `write_roots`; needs policy `allow_destructive=true`, else `DESTRUCTIVE_OPERATION_DISABLED`) |
| | `recursive` | no | default `false` (non-recursive dir delete only works when empty) |
| `process.run` | `argv` | yes | non-empty array of strings; `argv[0]` must be on the policy executable allowlist (`INVALID_ARGV` if malformed, `EXECUTABLE_NOT_ALLOWED` if not allowlisted). No shell: no pipes, globs, or `;` |
| | `cwd` | no | working directory (must be inside `read_roots`); default: first `read_root` |
| | `timeout_seconds` | no | clamped to 1..`max_timeout_seconds` (default 600); timeout = `BUILD_BROKEN`/`PROCESS_TIMEOUT` |
| `macos.open` | `value` | yes | app name (`mode:"app"`), path (`mode:"path"`, inside `read_roots`), or http(s) URL (`mode:"url"`, needs policy `allow_open_urls=true`) |
| | `mode` | no | `"path"` (default) \| `"app"` \| `"url"` |
| `macos.notify` | `title` | no | default `"ChatGPT local control"` |
| | `message` | no | notification body; default `""` |
| `macos.applescript.named` | `script_id` | yes | must match a key in the laptop's local `named_applescripts`; the script body is never sent over the bus |

### 4.4 Route A: file via git commit + push

```bash
EXPIRES=$(date -u -d '+10 minutes' +%Y-%m-%dT%H:%M:%SZ)   # GNU date; macOS: date -u -v+10M ...

cat > "${REQ_ID}.json" <<EOF
{
  "request_id": "${REQ_ID}",
  "operation": "system.snapshot",
  "machine": {"id": "*"},
  "expires_at": "${EXPIRES}",
  "payload": {}
}
EOF

cd lc-bus                                   # the single-branch clone from section 2
git fetch origin "$BRANCH"
git reset --hard "origin/$BRANCH"           # start from the current bus head
mv "${OLDPWD}/${REQ_ID}.json" "$REQ_PATH"
git add "$REQ_PATH"
git commit -m "request(local-control): ${REQ_ID}"
git push origin "HEAD:${BRANCH}"
```

If the push is rejected as non-fast-forward, someone advanced the bus: re-run the
`fetch` + `reset` + re-create the file + commit + push sequence (your `REQ_ID` timestamp
still keeps the id unique). If the file already exists on the branch, do NOT overwrite it —
pick a new `REQ_ID`.

### 4.5 Route B: file via `gh api` (no clone)

```bash
EXPIRES=$(date -u -d '+10 minutes' +%Y-%m-%dT%H:%M:%SZ)

cat > "${REQ_ID}.json" <<EOF
{
  "request_id": "${REQ_ID}",
  "operation": "system.snapshot",
  "machine": {"id": "*"},
  "expires_at": "${EXPIRES}",
  "payload": {}
}
EOF

CONTENT=$(base64 < "${REQ_ID}.json" | tr -d '\n')
gh api --method PUT \
  "repos/${REPO}/contents/${REQ_PATH}" \
  -f message="request(local-control): ${REQ_ID}" \
  -f content="$CONTENT" \
  -f branch="$BRANCH"
```

A `422` ("sha wasn't supplied") means the file already exists on the branch: mint a new
`REQ_ID`; never overwrite someone else's request.

## 5. Read the receipt

The agent writes `local-control/receipts/<request_id>.receipt.json` on the same branch and
pushes it. Poll with a bounded attempt count (never an unbounded loop).

Route A — git fetch loop (run from any clone of the repo):

```bash
ATTEMPTS=40          # 40 * 15s = 10 min; match your expires_at budget
N=1
while [ "$N" -le "$ATTEMPTS" ]; do
  git fetch origin "$BRANCH"
  if git show "FETCH_HEAD:local-control/receipts/${REQ_ID}.receipt.json" >/dev/null 2>&1; then
    git show "FETCH_HEAD:local-control/receipts/${REQ_ID}.receipt.json"
    exit 0
  fi
  N=$((N + 1))
  sleep 15
done
echo "NO_RECEIPT: ${REQ_ID} (standing UNKNOWN after ${ATTEMPTS} attempts)" >&2
exit 1
```

Route B — `gh api` loop:

```bash
N=1
while [ "$N" -le 40 ]; do
  if gh api "repos/${REPO}/contents/local-control/receipts/${REQ_ID}.receipt.json?ref=${BRANCH}" > /tmp/receipt.json 2>/dev/null; then
    gh api "repos/${REPO}/contents/local-control/receipts/${REQ_ID}.receipt.json?ref=${BRANCH}" \
      --jq '.content' | tr -d '\n' | base64 -d
    exit 0
  fi
  N=$((N + 1))
  sleep 15
done
echo "NO_RECEIPT: ${REQ_ID}" >&2
exit 1
```

### 5.1 Receipt fields

Top-level fields you will use: `standing`, `reason`, `error`, `result`, plus the binding
identity: `request_id`, `request_sha256`, `operation`, `machine_id`, `repo`, `branch`,
`started_at`, `completed_at`, `receipt_version` (always `1`). Verify `request_id` matches
yours and `machine_id` is the machine you targeted before trusting the rest.

### 5.2 Standing

| Standing | Meaning | What you do |
| --- | --- | --- |
| `ALIVE` | the operation executed on the laptop; `result` holds the output | read `result` |
| `REFUSED` | a local law rejected the request (scope/expiry/replay/operation/path/executable/platform); see `reason`/`error` | this is a correct outcome, not an error to retry blindly — fix the request class or stop |
| `BUILD_BROKEN` | the request was admitted but execution machinery failed (timeout, missing payload key, runtime exception); see `reason`/`error` | correct your payload and file a fresh id |
| `UNKNOWN` | no receipt at all (agent offline, expired before pickup, still pending) | check the laptop is enrolled/running or ask the operator; never re-file the same id |

### 5.3 Reason taxonomy

`REFUSED` reasons (exact strings from the agent):

| Reason | Meaning |
| --- | --- |
| `MISSING_REQUEST_ID` | request carried no `request_id` |
| `REQUEST_ID_PATH_MISMATCH` | JSON `request_id` does not equal the filename stem |
| `MACHINE_SCOPE_VIOLATION` | `machine.id` is neither `"*"` nor this laptop's configured id |
| `REQUEST_EXPIRED` | `expires_at` is already in the past |
| `REPLAY_DETECTED` | this `request_id` executed before (local replay ledger, independent of Git history) |
| `OPERATION_NOT_ALLOWED` | operation not in the laptop's `allowed_operations` |
| `UNSUPPORTED_OPERATION` | operation has no implementation in the agent |
| `READ_PATH_NOT_ALLOWED` | target path outside policy `read_roots` (or no read roots configured) |
| `WRITE_PATH_NOT_ALLOWED` | target path outside policy `write_roots` (or no write roots configured) |
| `EXECUTABLE_NOT_FOUND` | `process.run` executable does not exist on the laptop |
| `EXECUTABLE_NOT_ALLOWED` | resolved executable not in policy `allowed_executables` |
| `NOT_A_DIRECTORY` | `filesystem.list` target is not a directory |
| `INVALID_ARGV` | `process.run` `argv` is not a non-empty array of strings |
| `DESTRUCTIVE_OPERATION_DISABLED` | `filesystem.delete` while policy has `allow_destructive=false` |
| `UNSUPPORTED_PLATFORM` | macOS-only operation requested on a non-macOS host |
| `APP_NOT_ALLOWED` | `macos.open` app not in policy `allowed_apps` |
| `OPEN_URLS_DISABLED` | `macos.open` URL mode while policy has `allow_open_urls=false` |
| `URL_SCHEME_NOT_ALLOWED` | `macos.open` URL is not `http://`/`https://` |
| `INVALID_OPEN_MODE` | `macos.open` `mode` is not `app`/`path`/`url` |
| `APPLESCRIPT_NOT_ALLOWED` | `script_id` not present in the laptop's local `named_applescripts` |

`BUILD_BROKEN` reasons:

| Reason | Meaning |
| --- | --- |
| `PROCESS_TIMEOUT` | admitted `process.run` exceeded its (clamped) timeout |
| `<ExceptionClass>` (e.g. `KeyError`, `FileNotFoundError`, `PermissionError`) | unexpected runtime failure; `error` carries the message. Missing a required payload key surfaces as `KeyError` |

A timezone-less `expires_at` also lands here as `BUILD_BROKEN` (`ValueError: timestamp
must include timezone`). Malformed JSON in a request file may produce no receipt at all
(the agent logs it and moves on) — treat persistent silence as `UNKNOWN` and verify your
JSON before re-filing under a new id.

## 6. Worked example end-to-end

```bash
REPO=seanchatmangpt/chatgpt-cloud-elixir
BRANCH=local-control-bus
INSTANCE=ccx1
TS=$(date -u +%Y%m%dT%H%M%SZ)
REQ_ID="${INSTANCE}-${TS}-snapshot"
REQ_PATH="local-control/requests/${REQ_ID}.json"
EXPIRES=$(date -u -d '+10 minutes' +%Y-%m-%dT%H:%M:%SZ)

# 1. file (gh route; git route shown in 4.4)
cat > "${REQ_ID}.json" <<EOF
{
  "request_id": "${REQ_ID}",
  "operation": "system.snapshot",
  "machine": {"id": "*"},
  "expires_at": "${EXPIRES}",
  "payload": {}
}
EOF
CONTENT=$(base64 < "${REQ_ID}.json" | tr -d '\n')
gh api --method PUT "repos/${REPO}/contents/${REQ_PATH}" \
  -f message="request(local-control): ${REQ_ID}" \
  -f content="$CONTENT" -f branch="$BRANCH"

# 2. poll for the receipt
N=1
while [ "$N" -le 40 ]; do
  if gh api "repos/${REPO}/contents/local-control/receipts/${REQ_ID}.receipt.json?ref=${BRANCH}" >/tmp/rcpt.json 2>/dev/null; then
    gh api "repos/${REPO}/contents/local-control/receipts/${REQ_ID}.receipt.json?ref=${BRANCH}" \
      --jq '.content' | tr -d '\n' | base64 -d
    break
  fi
  N=$((N + 1)); sleep 15
done

# 3. learn the laptop id from the receipt, use it for all later requests
#    "machine_id": "sean-mac"   ->   "machine": {"id": "sean-mac"}
```

A follow-up read, once the id is known:

```bash
REQ_ID="${INSTANCE}-$(date -u +%Y%m%dT%H%M%SZ)-readfile"
cat > "${REQ_ID}.json" <<EOF
{
  "request_id": "${REQ_ID}",
  "operation": "filesystem.read",
  "machine": {"id": "sean-mac"},
  "expires_at": "$(date -u -d '+10 minutes' +%Y-%m-%dT%H:%M:%SZ)",
  "payload": {"path": "~/Projects/example/notes.txt", "max_bytes": 4096}
}
EOF
```

`result.content` holds the text, `result.truncated` tells you if it was clipped, and
`result.sha256` is the digest of the full original file.

## 7. Common mistakes

- Putting the id in the JSON but a different filename (or vice versa) → `REQUEST_ID_PATH_MISMATCH`.
- Reusing a `request_id`, even one whose receipt you deleted → `REPLAY_DETECTED`.
- Omitting `expires_at` timezone → `BUILD_BROKEN` (`ValueError`), not `REQUEST_EXPIRED`.
- Sending a shell string to `process.run` (`argv` must be an array; there is no shell).
- Assuming a path is readable: every path is checked against the laptop's policy roots.
- Retrying a `REFUSED` with the same shape: the refusal is the policy speaking. Re-derive
  or stop.
