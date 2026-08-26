# ChatGPT Cloud Process Intelligence Control Plane

This Phoenix/Ash application is the persistent operational projection of the
source-bound `process-intelligence` capsule.

It deliberately does **not** replace the offline capsule crown. The capsule
proves exact transported execution; this service continuously observes and
projects admitted OCEL events from agents, CI, ex4pm, AshR2RML, and other
producers.

## Surfaces

- `/process-intelligence/live` — Phoenix LiveView streaming OCEL feed.
- `/admin` — AshAdmin over the persisted process-intelligence Ash resources.
- `/api/v1/ocel/batches` — authenticated `chatgpt-cloud-ocel/1` ingestion.
- `/healthz` — database-backed health check used by Fly.
- `/mcp` — AshAi/MCP junction, including read-only Project Two semantic projections.

Browser routes use HTTP Basic Auth from `ADMIN_USERNAME` / `ADMIN_PASSWORD`.
The ingest API requires `Authorization: Bearer $OCEL_INGEST_TOKEN`.

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
dashboard, and authenticated ingest crown to execute against the admitted app.
