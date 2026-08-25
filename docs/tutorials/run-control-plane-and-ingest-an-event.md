# Tutorial: Run the Control Plane Locally and Ingest One OCEL Event

The control plane (`control-plane/`) is a Phoenix/Ash application that receives
OCEL (Object-Centric Event Log) batches from producers, stores them, and shows
them live in a dashboard. This tutorial gets it running on your machine and walks
through sending it one real event with `curl`, then seeing it land.

## Prerequisites

- Elixir/Erlang matching `control-plane/.tool-versions` (Erlang `29.0`, Elixir
  `1.20.2-otp-29`). If you don't have these installed system-wide, you can supply
  them via a `beam-core` or `ash-full` capsule from
  `docs/tutorials/manufacture-your-first-capsule.md` — activate it
  (`source <dest>/activate`) before running the commands below.
- A local Postgres reachable with user/password `postgres`/`postgres` on
  `localhost` (override via `PGUSER`/`PGPASSWORD`/`PGHOST`), Postgres 17.0.0 or
  newer.

## Step 1: Set up the app

```bash
cd chatgpt-cloud-elixir/control-plane
mix setup
```

This runs `deps.get`, `ecto.create`, `ecto.migrate`, `assets.setup`, and
`assets.build`.

## Step 2: Set the required environment variables

Dev mode has **no built-in fallback** for the admin Basic-Auth credentials — the
app will raise `ArgumentError` on your first browser request to `/` or `/admin` if
these aren't set (this is a real gap, not a hypothetical: `config/dev.exs` never
assigns `admin_username`/`admin_password`, and the auth plug uses
`Application.fetch_env!`, which raises rather than defaulting). Export both before
starting the server:

```bash
export ADMIN_USERNAME=dev
export ADMIN_PASSWORD=dev-password
export OCEL_INGEST_TOKEN=dev-ocel-token   # this is also dev.exs's own default if you skip it
```

## Step 3: Start the server

```bash
mix phx.server
```

Visit `http://localhost:4000/healthz` — you should get:

```json
{"status":"ok","standing":"ALIVE"}
```

(If you get `{"status":"database_unavailable","standing":"BLOCKED"}` with a `503`,
Postgres isn't reachable — check your `PGUSER`/`PGPASSWORD`/`PGHOST`.)

## Step 4: Open the live dashboard

Visit `http://localhost:4000/process-intelligence/live` in a browser. Log in with
the `ADMIN_USERNAME`/`ADMIN_PASSWORD` you exported. You should see a mostly-empty
dashboard (events/min, active agents, active runs, refusals/hour, process
variants) — this will update live once you post an event in the next step.

## Step 5: Ingest one real OCEL event

In a second terminal:

```bash
curl -X POST http://localhost:4000/api/v1/ocel/batches \
  -H 'content-type: application/json' \
  -H 'authorization: Bearer dev-ocel-token' \
  -d '{
    "schema": "chatgpt-cloud-ocel/1",
    "producer": {
      "agent_id": "local-agent",
      "run_id": "run-001",
      "subject_repo": "seanchatmangpt/chatgpt-cloud-elixir",
      "subject_sha": "deadbeef"
    },
    "events": [
      {
        "activity": "ci.build",
        "sequence": 1,
        "timestamp": "2026-08-25T00:00:00Z",
        "standing": "ALIVE",
        "authority_domain": "OBSERVE"
      }
    ]
  }'
```

You should get back `202 Accepted` with a body like:

```json
{"accepted_events": 1, "duplicate_events": 0, "run_key": "...", "agent_key": "...", "standing": "ALIVE"}
```

The `Bearer` token must match `OCEL_INGEST_TOKEN` exactly, or you get `401
{"error":"unauthorized"}`.

## Step 6: Watch it land live

Switch back to the dashboard tab from Step 4 — the event you just posted should
appear via the live PubSub feed (`process-intelligence:ocel` topic) without
reloading the page, and the rolling stats should update.

## Step 7: Send the same event again (idempotency check)

Run the exact same `curl` command from Step 5 again. This time the response
should show:

```json
{"accepted_events": 0, "duplicate_events": 1, ...}
```

Ingestion is idempotent by natural key — resending the same event key does not
create a duplicate row and does not re-broadcast to the dashboard.

## Step 8: Try the admin UI

Visit `http://localhost:4000/admin` (same Basic-Auth credentials) to browse every
Ash resource — agents, runs, events, objects, receipts, qualifications, cost
observations, and more — via AshAdmin's generic CRUD interface.

## What's next

- `scripts/emit-ocel.py` (used by CI) generates envelopes in this same shape from
  CLI flags, if you'd rather script event emission than hand-write JSON.
- For the full envelope schema (every optional field: `receipts`,
  `conformance_results`, `refusals`, `process_variants`, `object_relationships`),
  the standing vocabulary, and every route in the router, see `docs/reference/`.
- For why ingestion writes directly via `Repo.insert_all` instead of through Ash's
  changeset pipeline, and how this differs from the `Qualification` state machine
  that separately reconciles receipts into pass/fail decisions once a minute, see
  `docs/explanation/`.
- The same Bearer token also unlocks `/graphql`, `/api/json/*`, and `/mcp` (the
  AshAi MCP tool server) — there is no separate credential tier for those.
