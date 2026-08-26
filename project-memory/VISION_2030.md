# Project Two Vision 2030

Vision 2030 is a deterministic, read-only portfolio projection over the same
canonical GitHub Project v2 #2 semantic graph used by the Project-memory bus and
the AshAi/MCP control plane.

It is not a forecast model and it does not create actuation authority. Its job is
to make the current evidence base legible as an autonomous software-manufacturing
portfolio and to expose where the evidence does not yet support the intended
capability horizon.

## Interfaces

| Plane | Operation / tool | Implementation |
| --- | --- | --- |
| Receipted request bus | `project.vision2030` | `scripts/project_vision_2030.py` |
| Ash action | `:vision_2030` | `ChatGPTCloud.DfcmMemory.SemanticVision2030` |
| AshAi/MCP | `project_vision_2030` | `ChatGPTCloud.DfcmMemory` domain tool |

All three surfaces consume the existing semantic graph. None introduces another
persistent database or another canonical subject.

## 2030 capability pillars

The projection searches admitted Project-memory evidence for eight explicit
capability families:

1. deterministic manufacture;
2. governed actuation;
3. autonomous qualification;
4. cloud execution;
5. process intelligence;
6. semantic interoperability;
7. agent evaluation;
8. portfolio memory.

A pillar is `PRESENT` only when its configured minimum number of distinct memory
records carry matching evidence. The default minimum is one record. Callers can
raise `minimum_evidence` to make the admission threshold stricter; the threshold
is reported back with each pillar so a single observation cannot silently become
an enterprise-readiness claim.

Signal matching is deliberately observational. It can identify candidate
capability evidence; it cannot grant `ALIVE`, prove standards conformance, or
replace the repository's exact-head CI courts.

## Evidence coverage

For every Project-memory record, the projection reports aggregate coverage for:

- explicit standing;
- repository identity;
- commit identity derived from SHA-bearing metadata edges;
- receipt or replay relationships.

Coverage is emitted as raw counts plus a ratio. Ratios are descriptive, not a
weighted maturity score.

## Dependency closure

`REQUIRES`, `DEPENDS_ON`, and `CONSUMES_MEMORY` edges are treated as explicit
dependency evidence. A memory-key target is considered closed only when that key
is also present among current Project-memory records.

The result contains:

- total dependency edges;
- resolved edges;
- unresolved edges;
- closure ratio;
- bounded unresolved-edge details.

This makes missing capability dependencies visible without manufacturing edges
from prose.

## Frontier ranking

The `frontier` list is a deterministic observational ordering of memory records.
It weights only evidence already present in the graph:

- exact metadata/commit evidence;
- receipt/replay evidence;
- explicit dependency relationships;
- explicit `ALIVE` standing;
- repository identity.

The rank is a navigation aid. It is not an optimizer, scheduler, priority grant,
or authorization decision. `frontier_limit` is bounded to 100.

## Authority law

Every result states:

```text
authority = READ_ONLY_VIRTUAL_PROJECTION
mutating_operations_introduced = 0
standing_granted = false
consequential_do_authority = false
```

Vision 2030 can expose a gap. Closing that gap still requires an existing bounded
mutation or manufacturing path, its normal receipts, and its normal exact-head
qualification.

## Falsifiers

The Vision 2030 projection is invalid if any of these occur:

1. it invents a dependency from free prose;
2. Python request-bus and Elixir/Ash implementations disagree on the authority law;
3. a pillar becomes `PRESENT` below the caller-visible evidence threshold;
4. a read invokes or obtains a Project mutation path;
5. an observational rank is treated as standing, authorization, or a merge decision;
6. exact-head tests/compile are bypassed because the projection itself returns data.

## Example request

```json
{
  "request_id": "project-two-vision-2030",
  "operation": "project.vision2030",
  "project": {"owner": "seanchatmangpt", "number": 2},
  "payload": {
    "query": {
      "minimum_evidence": 2,
      "frontier_limit": 25
    }
  }
}
```

The ordinary Project-memory receipt binds the request and result to the exact
Project subject and token-source class.
