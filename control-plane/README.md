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
- `/mcp` — AshAi/MCP junction, including read-only Project Two semantic projections.

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

## Project Two semantic PaaS

The `ChatGPTCloud.DfcmMemory` Ash domain wraps GitHub Project v2
`seanchatmangpt/2` as one canonical subject with multiple deterministic read
models. MCP clients can inspect the same Project as ordinary items, shared
memory, a property graph, bounded graph queries, relational tables, semantic
triples, JSON-LD, a service/capability catalog, OCEL-shaped process evidence,
or bounded LLM context.

These are virtual projections, not synchronized databases. Project #2 remains
the persisted subject; the projection tools carry `READ_ONLY_VIRTUAL_PROJECTION`
authority and do not convert graph paths, ontology facts, or model output into
ambient execution authority. Existing Project-memory writes remain separately
bounded and receipted.

The MCP surface earns control-plane standing only through the repository's
normal qualification sequence: canonical formatting, strict compile, test DB
migration, Ash ecosystem verification, application tests, production release,
and Docker-image construction. A successful projection fixture or Project-bus
receipt cannot substitute for those runtime gates. Both `feat/**` and
`feature/**` control-plane pushes enter those exact-head courts.

The Python Project-memory verifier is an independent projection-law gate; its
success transfers only while its Python source, tests, and workflow inputs are
unchanged.

See `../project-memory/SEMANTIC_VIRTUALIZATION.md` for the projection law,
operations, standing boundaries, and OCEL conformance caveat.

## Vision 2030 portfolio projection

`project_vision_2030` is the AshAi/MCP read surface for the deterministic
Project Two Vision 2030 model. The receipted request bus exposes the same model
as `project.vision2030`.

The projection reports eight autonomous-software-manufacturing capability
pillars, explicit evidence coverage, dependency closure, and a bounded frontier
ranking. `minimum_evidence` is caller-visible and turns insufficiently supported
pillars into explicit `GAP` results rather than inferred readiness.

The post-LLM projection additionally measures independent evidence-domain
coverage, qualified reusable manufacturing capital, observed combinatorial
capability pairings, and a maximalist gap frontier. Its fail-closed autonomy
envelope can report structural integration only when capability, dependency,
source-completeness, and caller-selected receipt-coverage conditions all hold.
Even then, the envelope remains `OBSERVATIONAL_ONLY`.

Vision 2030 parity now enters the same exact-head control-plane court as the
Ash runtime: Project-memory, semantic, and Vision Python tests run before the
canonical Elixir formatter, strict compilation, database migration, Ash
ecosystem verification, application tests, production release, and Docker
construction. This makes semantic parity and runtime qualification one evidence
chain instead of two unrelated green checks.

Vision 2030 is observational only. Every result is bound to
`READ_ONLY_VIRTUAL_PROJECTION`; it introduces zero mutating operations, grants
no standing, and carries no consequential `DO` authority. Gap closure still
requires an existing bounded manufacturing or mutation path plus its ordinary
receipts and exact-head qualification.

See `../project-memory/VISION_2030.md` for capability pillars, dependency law,
frontier ranking, and falsifiers.

## Local

```bash
mix setup
OCEL_INGEST_TOKEN=dev-ocel-token mix phx.server
```

Post a batch:

```bash
curl -X POST http://localhost:4000/api/v1/ocel/batches \
  -H 'content-type: application/json' \
  -H 'authorization: Bearer $OCEL_INGEST_TOKEN' \
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
