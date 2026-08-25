# Environment Variables

Every environment variable found across `capsules/`, `control-plane/`, and CI
workflows, what it configures, and where it's read.

## Capsule / capsule-build scripts

| Variable | Where read | Purpose |
|---|---|---|
| `GITHUB_SHA` | `scripts/build-capsule.sh` and related build scripts; CI workflows | Binds the capsule identity to the exact commit under proposal; CI sets this automatically, local builds must export it manually |
| `CAPSULE_OTP_OVERRIDE` | `scripts/build-capsule.sh` | Overrides `versions.toml [runtime].otp` for a single build |
| `CAPSULE_ELIXIR_OVERRIDE` | `scripts/build-capsule.sh` | Overrides `versions.toml [runtime].elixir` for a single build |
| `CAPSULE_ARCHIVE_DIGEST` | `scripts/run-offline.sh`, `verify-capsules.yml` | Expected sha256 of the capsule archive, checked before offline replay |
| `HTTP_PROXY` / `HTTPS_PROXY` / `ALL_PROXY` | `scripts/run-offline.sh` | Set to a loopback unlistened port (`http://127.0.0.1:9`) to force any accidental network call to fail fast, used as the fallback offline-proof mechanism when `unshare -n` isn't available |
| `ELIXIR_ERL_OPTIONS` | `scripts/run-offline.sh` | Set to `+fnu` to force UTF-8 filename handling |
| `POSTGRES_STATE_DIR` | `scripts/postgres-server.sh` | Overrides the default `state/postgres` cluster data directory |
| `PGHOST` / `PGPORT` | `postgres17` capsule `activate` script | Set to `127.0.0.1` / `55432` on activation |
| `POSTGRES_ROOT` | `postgres17` capsule `activate` script | Root path of the activated PostgreSQL capsule install |
| `GGEN_MARKETPLACE_ROOT` / `SWARMSH_ROOT` / `SWARMSH_V2_ROOT` | `autonomic-manufacturing` capsule `activate` script | Root paths of the activated ggen-marketplace / SwarmSH v1 / SwarmSH v2 source trees |

## `control-plane/` (Phoenix/Ash app)

| Variable | Where read | Required in | Purpose |
|---|---|---|---|
| `DATABASE_URL` | `config/runtime.exs` | prod (raises if missing) | Postgres connection string |
| `SECRET_KEY_BASE` | `config/runtime.exs` | prod (raises if missing) | Phoenix session/cookie signing key |
| `OCEL_INGEST_TOKEN` | `config/runtime.exs`, `config/dev.exs` | prod (raises); dev defaults to `"dev-ocel-token"` | Bearer token required on `/api/v1/ocel/batches`, `/graphql`, `/api/json`, `/mcp` |
| `ADMIN_USERNAME` | `config/runtime.exs` via `AdminAuth` (`Application.fetch_env!`) | prod (raises); **no dev default** — `dev.exs` sets `browser_auth_required` implicitly `true` but never assigns this key, so a bare `mix phx.server` will raise on the first browser request to `/` or `/admin` unless exported manually | HTTP Basic Auth username for `/`, `/process-intelligence/live`, `/admin` |
| `ADMIN_PASSWORD` | same as `ADMIN_USERNAME` | same caveat as `ADMIN_USERNAME` | HTTP Basic Auth password |
| `CLOAK_KEY_BASE64` | `config/runtime.exs` | prod (raises; must base64-decode to exactly 32 bytes) | `AshCloak` encryption key for `SecretCredential` |
| `PORT` | `config/runtime.exs` | optional, default `4000` | HTTP listen port |
| `POOL_SIZE` | `config/runtime.exs` | optional, default `10` | Ecto connection pool size |
| `ECTO_IPV6` | `config/runtime.exs` | optional | Forces IPv6 for the Ecto/Postgres connection |
| `PHX_HOST` | `config/runtime.exs` | optional | Public host name used for URL generation |
| `PHX_SERVER` | `config/runtime.exs` | optional | When set, starts the Phoenix endpoint under `mix release` (standard Phoenix release convention) |
| `PGUSER` / `PGPASSWORD` / `PGHOST` | `config/dev.exs` | dev, defaults `postgres`/`postgres`/`localhost` | Local dev Postgres connection |
| `DFCM_MEMORY_PROJECT_OWNER` / `DFCM_MEMORY_PROJECT_NUMBER` | documented in `config.exs`'s comment as overridable "via config/runtime.exs" — **not actually implemented**: `runtime.exs` at current HEAD has no code reading either name | n/a | Aspirational override for the DfCM Project owner/number; the compiled defaults (`"seanchatmangpt"` / `2`) are used regardless of environment until this is implemented |
| `PROJECTS_TOKEN` / `GH_TOKEN` / `GH_PAT` / `GITHUB_PAT` / `GITHUB_TOKEN` | `GithubProjectClient.resolve_token/0` (control-plane) | at least one required for DfCM memory access to succeed | GitHub token for the Project v2 GraphQL API; resolved in this exact precedence order, first non-empty value wins |

## Deploy (`deploy-fly.yml`)

| Variable | Where read | Purpose |
|---|---|---|
| `FLY_API_TOKEN` (secret) | `deploy-fly.yml` | Fly.io API token; workflow exits `69` with a `BLOCKED:` message if absent |
| `FLY_DEPLOY_ENABLED` (repo var) | `deploy-fly.yml` | Gates push-triggered deploys; manual `workflow_dispatch` runs regardless of this value |
| `FLY_APP_NAME` (repo var) | `deploy-fly.yml` | Target Fly app name; falls back to `chatgpt-cloud-process-intelligence` if unset and no dispatch input given |

## `project_memory_proxy.py` / `project-memory-proxy.yml`

| Variable | Where read | Purpose |
|---|---|---|
| `PROJECTS_TOKEN` / `GH_TOKEN` / `GH_PAT` / `GITHUB_PAT` (secrets) → `GITHUB_TOKEN` (repo fallback) | `.github/workflows/project-memory-proxy.yml` "Execute bounded Project v2 requests" step | Same precedence-resolved token source as the control-plane DfCM client, used to authenticate the Python proxy's GraphQL calls against Project `seanchatmangpt/2` |

See also: `docs/reference/status-vocabulary.md` for the `BLOCKED[IRREDUCIBLE_AUTHORITY]`
standing produced when no usable token is found; `docs/reference/mcp-tools.md` for how
`OCEL_INGEST_TOKEN` gates every `/mcp` tool call.
