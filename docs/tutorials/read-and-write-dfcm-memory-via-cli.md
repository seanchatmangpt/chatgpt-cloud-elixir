# Tutorial: Read and Write DfCM Memory via the Proxy CLI

GitHub Project v2 board `seanchatmangpt/2` is used as durable, structured, shared
memory across manufacturing runs and agent sessions. This tutorial walks you
through writing your first memory record and reading it back, using
`scripts/project_memory_proxy.py` directly from the command line — no running
server required. (The MCP transport in `control-plane/` reaches the same board
over `/mcp`, but needs a deployed or locally running Phoenix app; this tutorial
uses the CLI path instead, which works standalone.)

## Prerequisites

- Python 3 (the proxy is stdlib-only — no `pip install` needed).
- A GitHub token with access to Project `seanchatmangpt/2`, available in your
  environment as one of (checked in this order): `PROJECTS_TOKEN`, `GH_TOKEN`,
  `GH_PAT`, `GITHUB_PAT`, or `GITHUB_TOKEN`.
- A checkout of this repository.

If no usable token is present, or the resolved token can't reach the Project, the
proxy will not pretend the write succeeded — it reports
`BLOCKED[IRREDUCIBLE_AUTHORITY]` instead of a false `ALIVE`.

## Step 1: Run the test suite first (optional but recommended)

Before touching the live Project, confirm the proxy's pure/local logic is sound:

```bash
cd chatgpt-cloud-elixir
python3 -m unittest tests/test_project_memory_proxy.py
```

This exercises the request validation, the `<!-- chatgpt-project-memory:v1 ... -->`
body encode/decode round trip, and scope-rejection logic. It does not make any
real GitHub call — no network path is exercised by this suite.

## Step 2: Write a request file

Every operation is a JSON file. Create one for a `memory.upsert` (create-or-update
by key, never a blind overwrite — it always reads the current record first):

```bash
mkdir -p /tmp/dfcm-request
cat > /tmp/dfcm-request/my-first-memory.json <<'EOF'
{
  "request_id": "20260825T120000Z-my-first-memory",
  "operation": "memory.upsert",
  "project": {"owner": "seanchatmangpt", "number": 2},
  "payload": {
    "record": {
      "key": "tutorial/my-first-memory",
      "title": "Tutorial test record",
      "kind": "note",
      "cell": "MEASURE",
      "standing": "ALIVE",
      "tags": ["tutorial"],
      "body": "Written by the read-and-write-dfcm-memory tutorial.",
      "metadata": {"E": 1}
    }
  }
}
EOF
```

`project.owner`/`project.number` must be exactly `seanchatmangpt`/`2` — any other
value is refused as `REFUSED[PROJECT_SCOPE_VIOLATION]` before any GraphQL call is
made. Only the operation names in the proxy's allowlist are accepted (`project.
snapshot`, `project.items`, `memory.create`, `memory.read`, `memory.update`,
`memory.upsert`, `memory.query`, `memory.archive`, `memory.delete`) — raw GraphQL
is never accepted.

## Step 3: Run the proxy against your request

```bash
python3 scripts/project_memory_proxy.py \
  --request /tmp/dfcm-request/my-first-memory.json \
  --receipt /tmp/dfcm-request/my-first-memory.receipt.json
```

## Step 4: Read the receipt

```bash
cat /tmp/dfcm-request/my-first-memory.receipt.json
```

Look at the `standing` field:

- `ALIVE` — the mutation ran and returned; `result` contains
  `{"action": "created"|"updated", "record": {...}}`.
- `BLOCKED` with `reason: "IRREDUCIBLE_AUTHORITY"` — your token can't reach the
  Project. Check which token source you have set.
- `REFUSED[...]` — the request itself was rejected before any network call
  (wrong project scope, invalid operation, duplicate key on `memory.create`, or a
  key not found on `memory.read`/`update`).
- `UNKNOWN` — a network failure or an unclassified GraphQL error.
- `BUILD_BROKEN` — the proxy script itself threw, which is a defect in the proxy,
  not in your request.

Secrets are never written to the receipt — only the *source class* of the token
used (e.g. `"PROJECTS_TOKEN secret"`), never its value.

## Step 5: Read the record back

Write a second request file for `memory.read`:

```bash
cat > /tmp/dfcm-request/read-it-back.json <<'EOF'
{
  "request_id": "20260825T120100Z-read-it-back",
  "operation": "memory.read",
  "project": {"owner": "seanchatmangpt", "number": 2},
  "payload": {"key": "tutorial/my-first-memory"}
}
EOF

python3 scripts/project_memory_proxy.py \
  --request /tmp/dfcm-request/read-it-back.json \
  --receipt /tmp/dfcm-request/read-it-back.receipt.json

cat /tmp/dfcm-request/read-it-back.receipt.json
```

You should see your record's `title`, `body`, and `metadata` back, decoded from
the `<!-- chatgpt-project-memory:v1 <base64url(json)> -->` marker stored in the
underlying Project draft-issue body.

## Step 6 (in this repository's normal flow): commit the request instead of running it ad hoc

In the actual repository workflow, you would not usually run the proxy directly
against your local token. Instead you commit the request file under
`project-memory/requests/` and push it — `.github/workflows/
project-memory-proxy.yml` picks it up, runs the same test suite as a gate, resolves
a token from repository secrets, runs the proxy, and commits the resulting receipt
back to `project-memory/receipts/`. Running the CLI directly, as this tutorial
does, is useful for local development and debugging before you commit a request.

## What's next

- For the full list of the 9 operations, their exact request/result JSON shapes,
  and the DfCM memory-key convention (`dfcm/frontier/current`,
  `dfcm/measure/latest`, etc.), see `docs/reference/`.
- For why the Project board — not either transport — is the authoritative store,
  and how the Elixir/MCP transport in `control-plane/` mirrors this same protocol,
  see `docs/explanation/`.
- For calling the same operations over MCP once you have `control-plane` running,
  see `docs/tutorials/run-control-plane-and-ingest-an-event.md` to get the app up
  first, then use the `read_dfcm_memory` / `upsert_dfcm_memory` /
  `snapshot_dfcm_project` / `list_project_items` tools at `/mcp`.
