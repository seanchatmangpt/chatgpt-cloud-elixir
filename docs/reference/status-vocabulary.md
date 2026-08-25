# Status Vocabulary

The repo-wide standing vocabulary, used across capsules, `versions.toml`,
`control-plane/` receipts, `project_memory_proxy.py` receipts, and CI workflow
output. `versions.toml`'s `[standing].allowed` is the canonical closed list of the
six base values; `REFUSED_*` and `REFUSED[...]` are a separate, open-ended typed
family layered on top for protocol-level rejections.

## Base standing values (`versions.toml [standing].allowed`)

| Value | Meaning | Evidence required |
|---|---|---|
| `UNKNOWN` | Not observed / insufficient evidence | Default state before anything has run |
| `PARTIAL_ALIVE` | A lower execution boundary passed; the requested crown did not | e.g. construction succeeded but consumer replay hasn't run yet (a `build-receipt.json`'s own claim before the separate consumer-side `receipt.json` exists); or one component of a multi-part capsule is proven present/parseable but not runtime-executed (e.g. SwarmSH v2 typed-source ancestry) |
| `ALIVE` | The exact admitted subject executed the exact acceptance command successfully | A real acceptance command (e.g. `mix test`) exit code 0, captured in a `receipt.json` produced by the **consumer** verify script after a fresh extract — not the build script, not a green CI badge, not artifact/workflow existence alone |
| `BLOCKED` | An external capability or authority boundary prevented execution | e.g. a required host command missing (`command -v $cmd \|\| exit 69`); `unshare` unavailable; `setpriv` missing for a root consumer; a GitHub token that can't reach the Project (`BLOCKED[IRREDUCIBLE_AUTHORITY]`) |
| `BUILD_BROKEN` | A manufactured subject reached execution but violated its contract | Version mismatch (OTP/Elixir/PostgreSQL expected vs. observed), digest mismatch, missing manifest keys, non-capsule-local `erl`/`elixir`/`mix` binary, nonzero acceptance exit, non-deterministic ggen regeneration, or an unhandled exception in a proxy/verifier script itself |
| `UNSUPPORTED` | Requested platform/version/capability tuple is outside the admitted matrix | e.g. unknown capsule variant name, non-`linux_x86_64` platform, non-`github.com` source repository |

## The hard rule

Workflow existence, a green CI badge, an uploaded artifact, or a file literally named
`receipt.json` do **not**, by themselves, constitute `ALIVE`. Only a receipt produced
by a real local execution of the exact admitted subject counts (`AGENTS.md`: "A file
called `receipt.json` is not execution evidence").

Note the one systematic gotcha: every `build-*.sh` script's own `build-receipt.json`
self-labels `standing: ALIVE` for the *construction* phase only, with an explicit
note that consumer replay remains required. The separate consumer-side `receipt.json`
(written only by a verify script run against a genuinely fresh extraction) is what
the repo's own doctrine treats as authoritative for capsule-level `ALIVE`.

## Typed `REFUSED` family

Not part of the base six-value enum — a separate, open-ended vocabulary of
protocol-level rejections, always carrying a specific reason tag.

| Value | Where used | Meaning |
|---|---|---|
| `REFUSED[REPO_IDENTITY]` | R48 independent consumer court | Verification tool rejected a request because the subject repo identity didn't match the admitted contract (proven by a deliberate negative-control test in `r48-independent-consumer.yml`) |
| `REFUSED_FORMATTER_MUTATION` | `format-control-plane.yml` | `mix format` would have changed tracked source — the formatter itself produced a diff, not just failed `--check-formatted` |
| `REFUSED_INEXACT_FORMAT_SUBJECT` | `format-control-plane.yml` | Checked-out HEAD did not match the exact PR-head SHA the job was asked to format-check |
| `REFUSED[PROJECT_SCOPE_VIOLATION]` | `project_memory_proxy.py` | Request named a project owner/number other than `seanchatmangpt`/`2` |
| `REFUSED[INVALID_OPERATION]` | `project_memory_proxy.py` | Request named an operation outside the 9-operation allowlist (e.g. raw GraphQL) |
| `REFUSED[DUPLICATE_MEMORY_KEY]` | `project_memory_proxy.py` `memory.create` | Requested key already exists |
| `REFUSED[MEMORY_NOT_FOUND]` | `project_memory_proxy.py` `memory.read` | Requested key does not exist |
| `BLOCKED[IRREDUCIBLE_AUTHORITY]` | `project_memory_proxy.py` `GraphQLClient` | No usable token present, or a GraphQL 401/403/permission-scoped error — the proxy never pretends a mutation succeeded when authority is the actual blocker |

## OCEL ingestion standing field (`control-plane/`)

The OCEL envelope schema (`chatgpt-cloud-ocel/1`) accepts the same six base values
for `event.standing` (default `"UNKNOWN"`), plus any string prefixed `"REFUSED_"` is
also accepted as a valid `event.standing` value (open-ended, not a fixed enum member
— the ingestor pattern-matches the prefix rather than enumerating every possible
suffix).

See also: `docs/reference/versions-toml.md` for the `[standing]` table source;
`docs/reference/project-memory-protocol.md` for how these values appear in a proxy
receipt; `docs/explanation/` for why `ALIVE` is defined this strictly (the offline
law, "CI is never the crown").
