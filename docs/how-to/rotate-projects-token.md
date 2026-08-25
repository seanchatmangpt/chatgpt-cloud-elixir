# How to rotate or check the PROJECTS_TOKEN used for GitHub Project v2 memory access

Both memory transports (the Python/Action proxy and the Elixir/MCP
`ChatGPTCloud.DfcmMemory` domain) need a GitHub token that can read/write
Project `seanchatmangpt/2`. Neither transport has its own dedicated
credential — both resolve a token from environment/secrets in a fixed
precedence order.

## Token source precedence

Resolved in this exact order (first non-empty value wins), consistent
across both transports:

```
PROJECTS_TOKEN → GH_TOKEN → GH_PAT → GITHUB_PAT → GITHUB_TOKEN
```

- The Python proxy resolves this in the workflow step ("Execute bounded
  Project v2 requests") of `.github/workflows/project-memory-proxy.yml`,
  reading from GitHub Actions secrets.
- The Elixir/MCP `GithubProjectClient.resolve_token/0` resolves the same
  precedence from environment variables at runtime — `PROJECTS_TOKEN >
  GH_TOKEN > GH_PAT > GITHUB_PAT > GITHUB_TOKEN`.
- The last fallback, the ambient repository `GITHUB_TOKEN`, is used as a
  capability probe, not a guaranteed-to-work credential — org/user Projects
  are commonly not authorized by the ambient repo token, so a run falling
  through to it will often end up `BLOCKED`.

## To rotate the token

1. Generate a new GitHub personal access token (or fine-grained token) with
   Project read/write scope for `seanchatmangpt/2` — this is a manual step
   in GitHub's own settings; this repo does not automate PAT creation.
2. Update the `PROJECTS_TOKEN` secret in this repository's GitHub Actions
   secrets (repo Settings → Secrets and variables → Actions) so the
   workflow-triggered Python proxy picks it up on its next run.
3. Update the same value wherever `control-plane/` reads its runtime
   environment (e.g. Fly.io secrets for the deployed app, or your local
   `.env`/shell export for local development) so the Elixir/MCP transport
   resolves the same credential.
4. Confirm the old token is revoked in GitHub once the new one is
   confirmed working, to avoid two live credentials with the same scope.

## How to check whether the current token actually works

Submit a `project.snapshot` request (cheapest read-only check):

```json
{
  "request_id": "20260825T150000Z-token-check",
  "operation": "project.snapshot",
  "project": {"owner": "seanchatmangpt", "number": 2},
  "payload": {"max_items": 1}
}
```

Push it to `project-memory/requests/` and read the resulting receipt in
`project-memory/receipts/`:

- `standing: "ALIVE"` with a populated `result.project` — token works.
- `standing: "BLOCKED"`, `reason: "IRREDUCIBLE_AUTHORITY"` — no usable
  token was found, or the resolved token returned a 401/403 or an error
  message matching "resource not accessible" / "forbidden" / "permission" /
  "scope" / "could not resolve to a user". This is the proxy's explicit
  refusal to pretend a mutation succeeded when authority is the actual
  blocker — it never proceeds past this classification.

Equivalently, call `snapshot_dfcm_project` over `/mcp` from the Elixir/MCP
transport to check the credential `control-plane/` is currently running
with.

## Security notes

- Secrets are never logged or written to receipts by either transport —
  only the token's *source class* string (e.g. `"PROJECTS_TOKEN secret"`)
  is recorded, never the token value itself.
- `/mcp`, `/graphql`, and `/api/json` on the deployed control-plane all
  share the same `OCEL_INGEST_TOKEN` bearer credential — this is a
  different token from `PROJECTS_TOKEN` and gates access to the *control
  plane's own* endpoints, not GitHub Project access. Do not confuse the
  two when rotating credentials.

## See also

- [Add a new DfCM memory key](add-a-new-dfcm-memory-key.md)
- `docs/reference/` — full standing vocabulary for the memory proxy
- `docs/explanation/` — why neither transport is authoritative (the Project
  itself is)
