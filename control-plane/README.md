# ChatGPT Cloud Process Intelligence Control Plane

This Phoenix/Ash application is the persistent operational projection of the
source-bound `process-intelligence` capsule and the ChatGPT-side SwarmSH-style
work coordination surface.

It deliberately does **not** replace the offline capsule crown. The capsule
proves exact transported execution; this service continuously observes and
projects admitted OCEL events from agents, CI, ex4pm, AshR2RML, and other
producers.

## Surfaces

- `/process-intelligence/live` — Phoenix LiveView streaming OCEL feed.
- `/admin` — AshAdmin over the persisted process-intelligence Ash resources.
- `/api/v1/ocel/batches` — authenticated `chatgpt-cloud-ocel/1` ingestion.
- `/api/v1/swarm/work` — list/enqueue SwarmSH-style JSON work objects.
- `/api/v1/swarm/work/:id/{claim,progress,complete,block,refuse}` — atomic work transitions.
- `/api/v1/swarm/project2/import` — import Project #2 demand into deterministic work identities.
- `/healthz` — database-backed health check used by Fly.

Browser routes use HTTP Basic Auth from `ADMIN_USERNAME` / `ADMIN_PASSWORD`.
The control APIs require `Authorization: Bearer $OCEL_INGEST_TOKEN`.

## SwarmSH JSON work control

The control plane carries forward SwarmSH's useful coordination law without
copying its shell/filesystem implementation. A portable work envelope contains
`work_item_id`, claimant, reactor, source, work type, priority, team, status,
progress, subject, telemetry trace/span IDs, and an explicit authority fence.
PostgreSQL `FOR UPDATE` row locks replace advisory filesystem locks as the
atomic claim court.

Example enqueue:

```json
{
  "work_item_id": "work_example",
  "work_type": "implementation",
  "description": "manufacture the admitted change",
  "priority": "high",
  "team": "chatgpt_swarm",
  "subject": {
    "repository": "seanchatmangpt/chatgpt-cloud-elixir",
    "sha": "<exact admitted sha>"
  }
}
```

Every projected work object contains this non-overridable boundary:

```json
{
  "authority": {
    "select": {"granted": true},
    "construct": {"granted": true},
    "do": {"granted": false, "requires": "BRCE"}
  }
}
```

Incoming JSON cannot elevate `DO`. Claim, progress, completion, block, refusal,
and replay operations produce append-only `swarmsh.receipt/v1` records with a
SHA-256 digest and trace identity. `complete` always remains `PARTIAL_ALIVE`:
raw/model/planner completion JSON cannot self-crown execution standing. `ALIVE`
continues to belong to the independent exact-subject verification/receipt path.

Project #2 is demand, not the scheduler. Import maps each Project item to a
stable `project2_<digest>` work id, making repeated and concurrent imports
replayable instead of manufacturing duplicate work objects. Project-memory
records are control state and are excluded from work demand.

## Local

```bash
mix setup
OCEL_INGEST_TOKEN=dev-ocel-token mix phx.server
```

Post a batch:

```bash
curl -X POST http://localhost:4000/api/v1/ocel/batches \
  -H 'content-type: application/json' \
  -H 'authorization: Bearer dev-ocel-token' \
  -d @example.json
```

Enqueue and claim work:

```bash
curl -X POST http://localhost:4000/api/v1/swarm/work \
  -H 'content-type: application/json' \
  -H 'authorization: Bearer dev-ocel-token' \
  -d '{"work_item_id":"work_example","work_type":"implementation","description":"example"}'

curl -X POST http://localhost:4000/api/v1/swarm/work/work_example/claim \
  -H 'content-type: application/json' \
  -H 'authorization: Bearer dev-ocel-token' \
  -d '{"agent_id":"chatgpt-agent-1"}'
```

## Fly setup

The repository includes `fly.toml`, a release migration command, a production
Docker image, and `scripts/bootstrap-fly.sh`.

The bootstrap accepts one PostgreSQL admission path:

- `FLY_MPG_CLUSTER_ID` — existing Fly Managed Postgres cluster (preferred);
- `FLY_POSTGRES_APP` — existing unmanaged Fly Postgres cluster;
- `DATABASE_URL` — another admitted PostgreSQL provider.

Then run:

```bash
export FLY_APP_NAME=chatgpt-cloud-process-intelligence
export FLY_MPG_CLUSTER_ID=...
./scripts/bootstrap-fly.sh
```

The script creates the app when necessary, attaches/sets the database, stages
runtime secrets, deploys, and prints the generated admin/producer credentials
once. Fly secrets remain write-only after storage.

## GitHub deployment

`.github/workflows/deploy-fly.yml` is credential gated.

Required repository secret:

- `FLY_API_TOKEN`

Recommended repository variable:

- `FLY_APP_NAME`

Set `FLY_DEPLOY_ENABLED=true` only after the Fly app/database/secrets exist.
Manual `workflow_dispatch` remains available regardless of that variable.

## Standing

A successful CI image build proves the deployable artifact. It does not prove
Fly runtime standing. Fly `ALIVE` requires the release migration, health check,
dashboard, authenticated ingest crown, and—when Swarm coordination is in scope—
an observed authenticated enqueue/claim/progress/complete replay against the
admitted deployment.
