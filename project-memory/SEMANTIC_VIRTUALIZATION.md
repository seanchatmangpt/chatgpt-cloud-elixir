# Project Two Semantic Virtualization

Project Two (`seanchatmangpt/2`) is the canonical operational subject. It is **not** copied into a graph database, warehouse, RDF store, vector store, or process-mining database in order to gain those query models.

Instead, the bus follows the same architectural move as AshR2RML:

```text
                         GitHub Project v2 #2
                         (canonical subject)
                                  |
              +-------------------+-------------------+
              |                   |                   |
              v                   v                   v
         memory records      Project items       custom fields
              |                   |                   |
              +-------------------+-------------------+
                                  |
                                  v
                    deterministic semantic IR
                                  |
        +-----------+-------------+-------------+-----------+
        |           |             |             |           |
        v           v             v             v           v
 property graph   triples       tables       JSON-LD     OCEL-shaped
        |                                                   |
        +-------------------+-------------------------------+
                            |
                            v
                    LLM context + catalog
```

There is one subject and multiple lawful read models. No projection has ambient execution authority. Project memory mutations continue to go through the stable-key bounded operations and operation-level receipts.

## Virtual platform surface

The semantic layer makes Project Two inspectable as a small virtual semantic PaaS:

| Capability | Bus operation | MCP tool | Purpose |
| --- | --- | --- | --- |
| Canonical memory | `memory.*` | `read_dfcm_memory`, `upsert_dfcm_memory` | Stable cross-run/cross-agent state. |
| Full object store | `project.items` | `list_project_items` | Issues, PRs, drafts, fields, labels, assignees. |
| Property graph | `project.graph` | `project_property_graph` | Vertices and explicit evidence-backed edges. |
| Graph query | `project.graph.query` | `query_project_graph` | Filters and bounded neighborhood traversal. |
| Relational view | `project.tables` | `project_relational_tables` | Ordinary node/edge/fact rows for non-graph consumers. |
| Triple view | `project.triples` | `project_semantic_triples` | Subject/predicate/object projection. |
| JSON-LD | `project.jsonld` | `project_jsonld` | Linked-data projection with public vocabulary prefixes. |
| Service catalog | `project.services` | `project_service_catalog` | Interfaces, capabilities, resource facets. |
| Process view | `project.ocel` | `project_ocel` | OCEL-2-shaped event/object view; conformance not claimed until independently validated. |
| LLM context | `project.context` | `project_llm_context` | Bounded semantic neighborhood optimized for context windows. |
| Composite bundle | `project.semantic` | `inspect_project_semantics` | Any combination of the above views in one observation. |

Any MCP-capable model can therefore consume the same semantic subject through the AshAi junction. ChatGPT/scheduled cells use the request/receipt transport. Humans retain the ordinary GitHub Project UI. Non-graph software can use the tabular rows. Graph-aware software can use vertices/edges. Linked-data tooling can consume JSON-LD or triples.

## Admission law: explicit semantics only

The projector preserves information aggressively but infers relationships conservatively.

Edges are admitted from Project membership; repository identity; labels and assignees; memory key and tags; explicit relation-bearing metadata such as `memory_keys_consumed`, `memory_keys_updated`, `memory_created`, `dependencies`, `requires`, `unlocks`, `supersedes`, `derived_from`, `receipt`, `receipts`, and `replay`; and explicit SHA-bearing metadata fields.

Arbitrary prose remains a fact/literal. A sentence containing words such as “depends on” does **not** become a dependency edge. This prevents semantic hallucination from acquiring structural standing.

All scalar Project fields and memory metadata remain inspectable as facts even when they are not promoted to graph edges.

The semantic control-plane source itself is also subject to repository admission: the canonical `mix format --check-formatted` gate must pass before strict compile and the broader control-plane qualification can crown an exact head. Formatting is therefore manufactured, not waived, and never substitutes for compile/test execution.

## Public semantic vocabulary

The JSON-LD context uses public namespaces where the equivalence is defensible: PROV-O for provenance entities, DCAT for dataset/data-service framing, DCTERMS for general metadata vocabulary, SKOS for labels/tags as concepts, FOAF for actors/agents, and DOAP/Schema.org for source-code repositories.

Project-specific relations remain under a Project Two vocabulary namespace rather than being forced into a public ontology without equivalence proof.

## Graph query

`project.graph.query` and `project_llm_context` accept a bounded query map. Supported selectors include:

```json
{
  "text": "frontier",
  "types": ["MemoryRecord"],
  "repository": "seanchatmangpt/ggen-marketplace",
  "kind": "dfcm.frontier",
  "standing": "ALIVE",
  "tags": ["dfcm"],
  "predicates": ["CONSUMES_MEMORY"],
  "neighbors_of": ["urn:project-two:item:..."],
  "depth": 2,
  "direction": "both",
  "limit": 100,
  "max_body_chars": 1200
}
```

Neighborhood traversal is bounded. Read-model operations never mutate the Project and never turn graph reachability into permission to execute a consequence.

## PaaS / SaaS interpretation

Project Two can be viewed at several layers without changing its storage engine:

```text
GitHub Project v2                         operational substrate
Project memory protocol                  durable semantic KV service
Project item + field projection          object/document service
Virtual graph + graph query              graph service
Tables                                   relational/analytics service
Triples + JSON-LD                        linked-data service
OCEL-shaped projection                   process-evidence service
Service catalog                          capability-discovery service
LLM context                              semantic context service
AshAi / MCP                              model-neutral tool plane
GitHub UI                                human inspection plane
request + receipt workflow               receipted ChatGPT transport
```

This is virtualization, not rebranding: each service must be able to point back to the exact Project item/field/metadata that manufactured the projected fact or edge.

## Difference from a graph database

A graph database would make graph persistence authoritative. Project Two does not need that move.

```text
Project item/field/memory state == source of truth
virtual graph                  == projection of that state
```

This preserves GitHub's ordinary UI, issue/PR interoperability, Project field semantics, and the existing memory bus while adding graph expressiveness. It also means graph-schema evolution is reversible: change the projector, not the canonical operational data.

## OCEL standing

The process projection is intentionally labeled **OCEL-2-shaped** rather than “OCEL 2 conformant.” It creates Project-item / MemoryRecord objects, a semantic-snapshot observation event, and memory-created / memory-updated events when explicit timestamps exist. It does not acquire an `ALIVE` OCEL-conformance claim until an independent OCEL 2 validator executes against the exact generated payload.

## Falsifiers

The virtualization is invalid if any of the following occurs:

1. a projection silently invents a graph edge from unstructured prose;
2. two views disagree about the identity of the canonical Project item;
3. a read-model operation mutates Project state;
4. a projected fact cannot be traced to an item field, memory metadata, or deterministic projection rule;
5. an LLM tool gains raw GraphQL or actuation authority through the projection layer;
6. OCEL/JSON-LD standards conformance is claimed without an executed validator;
7. a second persistence layer becomes authoritative without an explicit architectural change.

## Example request

```json
{
  "request_id": "project-two-semantic-context-example",
  "operation": "project.context",
  "project": {"owner": "seanchatmangpt", "number": 2},
  "payload": {
    "query": {
      "types": ["MemoryRecord"],
      "tags": ["dfcm"],
      "depth": 1,
      "limit": 100,
      "max_body_chars": 1200
    }
  }
}
```

The receipt binds the exact request, Project identity, returned projection, token-source class, and standing through the same bus that already handles Project memory.
