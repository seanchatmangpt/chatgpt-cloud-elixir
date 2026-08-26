# Project Two Vision 2030

Vision 2030 is a deterministic, read-only portfolio projection over the same
canonical GitHub Project v2 #2 semantic graph used by the Project-memory bus and
the AshAi/MCP control plane.

It is not a forecast model and it does not create actuation authority. Its job is
to make the current evidence base legible as an autonomic software-manufacturing
portfolio and to expose where the evidence does not yet support the intended
capability horizon.

The governing design assumption is post-LLM: model output is not treated as the
system. Durable advantage is represented as reusable manufacturing capital,
qualified execution machinery, explicit authority law, semantic interoperability,
process evidence, evaluation machinery, and a memory substrate that compounds
those capabilities across future manufacture.

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

A pillar is `PRESENT` only when both caller-visible evidence thresholds hold:

- `minimum_evidence`: minimum number of distinct matching memory records;
- `minimum_domains`: minimum number of distinct evidence domains, where repository
  identity is the preferred domain and unbound Project memory is one shared domain.

The diversity gate is an anti-Goodhart control. Repeating many similar records
from one repository cannot silently simulate independent portfolio breadth. A
failed pillar reports typed falsifiers such as `EVIDENCE_SHORTFALL` and
`DOMAIN_DIVERSITY_SHORTFALL`.

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

## Manufacturing capital

`manufacturing_capital` separates reusable productive machinery from undifferentiated
activity. It classifies observed records into additive capital families:

- generative capital — generators, packs, marketplaces, manufacturing machinery;
- governance capital — authority, admission, receipts, replay, verification courts;
- qualification capital — CI, tests, validators, exact-head workflows;
- semantic capital — ontologies and deterministic semantic projections;
- execution capital — cloud/runtime/deployment machinery;
- evaluation capital — gyms, benchmarks, planners, policies, episodes;
- memory capital — durable portfolio memory, ledgers, frontiers, capability records.

A record counts as `qualified_reusable_capital` only when it is explicitly
`ALIVE` **and** has receipt/replay evidence. The report also exposes an
`unqualified_capital_frontier` so productive machinery that exists but lacks
standing or receipts cannot disappear inside aggregate counts.

This is a software-capital model, not a GAAP/IFRS capitalization claim.

## Dependency closure

`REQUIRES`, `DEPENDS_ON`, and `CONSUMES_MEMORY` edges are treated as explicit
dependency evidence. A memory-key target is considered closed only when that key
is also present among current Project-memory records.

The result contains total dependency edges, resolved edges, unresolved edges,
closure ratio, and bounded unresolved-edge details. Missing dependencies remain
falsifiers; no dependency is manufactured from prose.

## Combinatorial option space

Design for combinatorial maximalism is represented without inventing a fake
throughput number. `combinatorial_option_space` measures the topology actually
visible in evidence:

- all possible pairings among the eight capability pillars (28);
- distinct pillar pairings already co-occurring in Project-memory records;
- pairing coverage ratio;
- number of records spanning two or more pillars;
- the exact observed pair set.

This treats cross-capability integration as option stock. It does **not** claim
that a co-occurrence is causal, that all pairings have equal economic value, or
that pair count predicts commits per hour.

## Maximalist frontier

`maximalist_frontier` ranks **gaps by unrealized option surface**, not by cheapest
repair. For each missing pillar it reports:

- unrealized pairings with the other pillars;
- evidence shortfall;
- domain-diversity shortfall;
- an explicit option-surface score;
- the typed falsifiers preventing presence.

This is intentionally different from a minimum-effort backlog. The question is
"where can the system create the most additional combinatorial manufacturing
surface?", while preserving the rule that observation never authorizes DO.

## Autonomy envelope

`autonomy_envelope` is the fail-closed structural crown. It reports `CLOSED` only
when all configured structural conditions hold:

- the source is not truncated;
- all eight capability pillars are present under the caller's evidence/diversity law;
- there are no unresolved explicit dependencies;
- receipt/replay coverage meets `minimum_receipt_ratio`.

A closed envelope is labeled `INTEGRATED_AUTONOMIC_STACK` and still carries
`standing = OBSERVATIONAL_ONLY`. It is a structural statement about the evidence
graph, not production certification, safety certification, or permission to act.

An open envelope reports exact falsifiers such as `SOURCE_TRUNCATED`,
`CAPABILITY_GAPS`, `UNRESOLVED_DEPENDENCIES`, and
`RECEIPT_COVERAGE_SHORTFALL`.

## Frontier ranking

The legacy `frontier` remains a deterministic navigation ordering of memory
records using only evidence already present in the graph: commit metadata,
receipt/replay relationships, explicit dependencies, `ALIVE` standing, and
repository identity. It is not a scheduler or authorization decision.

## Merge-aware Project-memory admission

The Project-memory workflow is merge-aware. On ordinary commits it admits newly
added/modified request files. On merge commits it uses combined-diff semantics so
request files inherited unchanged from another parent become reachable without
being replayed as new requests. A request changed relative to every merge parent
remains admissible.

This distinction is required for autonomic repositories: integrating history is
not equivalent to re-actuating historical intent.

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
2. Python request-bus and Elixir/Ash implementations disagree on authority law;
3. a pillar becomes `PRESENT` below evidence or domain-diversity thresholds;
4. repeated evidence from one domain is counted as independent diversity;
5. a read invokes or obtains a Project mutation path;
6. manufacturing-capital classification is treated as financial accounting;
7. an observed pairing is represented as causal evidence or an effort estimate;
8. autonomy-envelope closure is treated as standing, authorization, or certification;
9. a merge replays request files merely because another parent made them reachable;
10. exact-head tests/compile are bypassed because the projection itself returns data.

## Example request

```json
{
  "request_id": "project-two-vision-2030",
  "operation": "project.vision2030",
  "project": {"owner": "seanchatmangpt", "number": 2},
  "payload": {
    "query": {
      "minimum_evidence": 2,
      "minimum_domains": 2,
      "minimum_receipt_ratio": 0.75,
      "frontier_limit": 25
    }
  }
}
```

The ordinary Project-memory receipt binds the request and result to the exact
Project subject and token-source class.
