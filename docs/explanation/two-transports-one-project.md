# Two Transports, One Project

The same GitHub Project v2 board (`seanchatmangpt/2`) is written to and read
from by two entirely independent implementations: a Python script invoked by a
GitHub Action, and an Elixir/Ash module exposed as MCP tools. This document
explains why there are two implementations instead of one shared library, and
what actually keeps them from silently diverging.

## The two transports

- **Transport A — the ChatGPT-side proxy** (`scripts/project_memory_proxy.py`,
  stdlib-only Python using `urllib`, no external dependencies). It is triggered
  by a GitHub Action whenever a request JSON file lands under
  `project-memory/requests/`, and it writes a typed receipt to
  `project-memory/receipts/`. It implements the full 9-operation protocol:
  `project.snapshot`, `project.items`, and `memory.create` / `read` / `update` /
  `upsert` / `query` / `archive` / `delete`.
- **Transport B — the Claude/MCP-side client**
  (`control-plane/lib/chatgpt_cloud_control_plane/dfcm_memory/`, Elixir/Ash,
  using Erlang's built-in `:httpc` — again, deliberately no new HTTP dependency
  added just for this). It is exposed live over `/mcp` as four AshAi tools:
  `read_dfcm_memory`, `upsert_dfcm_memory`, `snapshot_dfcm_project`, and
  `list_project_items`. It implements a real subset of the Python side's
  operation set — read, upsert, snapshot, and item-listing — with no separate
  `memory.create`/`archive`/`delete`/`query`-by-text tools (`read_dfcm_memory`'s
  Ash filter arguments cover query-style access on the MCP side instead of a
  dedicated query tool).

## Why two implementations rather than one shared library

The two transports run in genuinely different execution contexts, each of which
already has its own no-added-dependency discipline the memory client had to fit
inside rather than override:

- Transport A runs inside a GitHub Actions Python step with no BEAM runtime
  available at all — a shared Elixir library is not an option there.
- Transport B runs inside the control-plane Phoenix/Ash application, and is
  exposed as MCP tools specifically so a Claude session talking to
  `control-plane`'s `/mcp` endpoint can read and write the same memory without
  needing to shell out to Python or trigger a GitHub Action round trip.

Each side independently chose to avoid adding a new dependency for this: the
Python proxy uses only `urllib` from the standard library: the Elixir client
uses only `:httpc`, Erlang's built-in HTTP client, rather than pulling in an
HTTP client dependency. This is the same minimalism applied twice, in two
languages, not a coincidence — each transport is small and self-contained
enough that a shared library would add more coupling than it would remove
duplication.

Practically, a shared library would also have to be either an Elixir dependency
callable from Python (not workable) or a Python dependency callable from
Elixir (equally not workable) — the two run in disjoint language runtimes with
no natural third common host, so "one shared library" was never actually an
available option in the way it would be if both transports ran inside the same
language ecosystem.

## What keeps the two sides from silently diverging

Because there is no shared code, agreement between the two transports has to be
enforced by *convention*, checked in both places independently, rather than by
construction. Three concrete mechanisms:

1. **Hard project scope, identical on both sides.** Both transports pin
   `owner=seanchatmangpt`, `number=2` and refuse any request naming a different
   project — the Python proxy does this in `validate_request`
   (`REFUSED[PROJECT_SCOPE_VIOLATION]` on mismatch, and this behavior is
   directly unit-tested), and the Elixir side pins the same values via
   `config :chatgpt_cloud_control_plane, :dfcm_memory`. Neither side accepts a
   request that would let it write to a different board.

2. **A shared body-encoding marker, decoded identically on both sides.** Every
   memory record is stored as a Project draft issue whose body begins with a
   machine-readable HTML comment: `<!-- chatgpt-project-memory:v1
   <base64url(canonical-sorted-JSON)> -->`, followed by ordinary human-readable
   Markdown. Both transports encode and decode this marker independently — the
   Python side via `encode_memory_body`/`decode_memory_body`, the Elixir side
   via its own equivalent functions — and both canonicalize the JSON the same
   way before encoding: recursively sorted map keys, matching Python's
   `json.dumps(value, sort_keys=True, separators=(",",":"))` byte for byte. This
   canonicalization is deliberate, not incidental: ordinary JSON parsing does
   not care about key order, so the two sides would still be able to *read*
   each other's records even without matching canonicalization — but any
   external digest or comparison computed over the canonical form would
   silently diverge if the two sides sorted differently. Matching canonical
   form byte-for-byte is what makes such comparisons trustworthy across
   transports, not merely a stylistic nicety.

3. **The Project is authoritative, and both READMEs say so explicitly.**
   Neither transport is treated as the source of truth — the Project itself is.
   A memory record either side writes is immediately legible to the other on
   its very next read, because both are reading and writing the same live
   GraphQL API surface, not a cache or a mirror of it. There is no
   synchronization step, because there is nothing to synchronize — both sides
   are thin clients over one shared store.

## Where the two sides are known to differ, and why that is acceptable

The Elixir/MCP transport implements a strict subset of the Python proxy's
operation set (no `memory.create`/`archive`/`delete`/`query` as distinct MCP
tools). This is a real, current asymmetry, not a bug to be silently
normalized away in documentation: the MCP surface was built to cover the
operations a Claude session actually needs interactively (read, write,
snapshot, browse), while the Python proxy implements the full protocol because
it is the transport of record for the request-file/Action workflow, which is
expected to support every operation named in `project-memory/README.md`'s
protocol table. An MCP client that needs `memory.delete` or `memory.archive`
today has to go through the request-file path instead — there is no
Elixir-side tool for it yet.

## See also

- [shared-memory-philosophy.md](shared-memory-philosophy.md) — why a GitHub
  Project v2 board was chosen for this role in the first place, and the
  read-before-manufacture / write-after-manufacture contract both transports'
  callers are expected to follow
- [authority-model.md](authority-model.md) — the standing vocabulary
  (`ALIVE`/`REFUSED`/`BLOCKED[IRREDUCIBLE_AUTHORITY]`/`UNKNOWN`/`BUILD_BROKEN`)
  both transports' receipts use, including how each classifies a token that
  cannot reach the Project
- `docs/reference/` for the exhaustive per-operation request/result schema of
  both transports
