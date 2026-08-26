defmodule ChatGPTCloud.DfcmMemory do
  @moduledoc """
  The shared LLM junction over GitHub Project v2 `seanchatmangpt/2`.

  ChatGPT's request/receipt bus and every AshAi/MCP client observe the same
  Project. Memory mutation remains bounded to stable-key upserts; semantic
  graph/table/triple/catalog/process/context tools are read-only projections over
  that exact subject.
  """

  use Ash.Domain, extensions: [AshAi]

  tools do
    tool(:read_dfcm_memory, ChatGPTCloud.DfcmMemory.MemoryRecord, :read,
      description:
        "Read-before-manufacture: list current DfCM memory records from Project #2. " <>
          "Filter through the Ash query. Call before proposing or starting manufacturing work."
    )

    tool(:upsert_dfcm_memory, ChatGPTCloud.DfcmMemory.MemoryRecord, :upsert_record,
      description:
        "Write-after-manufacture: create-or-update a Project #2 memory record by stable key. " <>
          "This is a bounded mutation of the canonical Project, never a blind overwrite."
    )

    tool(:snapshot_dfcm_project, ChatGPTCloud.DfcmMemory.MemoryRecord, :snapshot,
      description: "Live identity and item/memory-record counts for Project #2. Read-only."
    )

    tool(:list_project_items, ChatGPTCloud.DfcmMemory.MemoryRecord, :project_items,
      description:
        "Full-fidelity Project #2 item read: issues/PRs/drafts, fields, labels, assignees, and content. Read-only."
    )

    tool(:inspect_project_semantics, ChatGPTCloud.DfcmMemory.MemoryRecord, :semantic_project,
      description:
        "One subject, many virtual views over Project #2. Select graph, tables, triples, JSON-LD, " <>
          "service catalog, OCEL-shaped process evidence, and LLM context without copying data to another store."
    )

    tool(:project_property_graph, ChatGPTCloud.DfcmMemory.MemoryRecord, :semantic_graph,
      description:
        "Read-only property graph over Project #2. Vertices include items, memory keys, repositories, actors, " <>
          "labels, tags, commits, and explicit references. Edges are created only from explicit fields/metadata."
    )

    tool(:query_project_graph, ChatGPTCloud.DfcmMemory.MemoryRecord, :semantic_graph_query,
      description:
        "Query or traverse the virtual Project #2 graph by text/type/repository/kind/standing/tags/predicate, " <>
          "or expand bounded neighborhoods from node ids. Read-only."
    )

    tool(:project_relational_tables, ChatGPTCloud.DfcmMemory.MemoryRecord, :semantic_tables,
      description:
        "Expose Project #2 as ordinary node/edge/fact rows so non-graph tooling can inspect the same graph subject. Read-only."
    )

    tool(:project_semantic_triples, ChatGPTCloud.DfcmMemory.MemoryRecord, :semantic_triples,
      description:
        "Expose Project #2 as RDF-shaped subject/predicate/object facts derived from explicit Project fields and memory metadata. Read-only."
    )

    tool(:project_jsonld, ChatGPTCloud.DfcmMemory.MemoryRecord, :semantic_jsonld,
      description:
        "JSON-LD projection of Project #2 using public PROV/DCAT/DCTERMS/SKOS/FOAF/DOAP namespaces plus bounded Project Two predicates. Read-only."
    )

    tool(:project_service_catalog, ChatGPTCloud.DfcmMemory.MemoryRecord, :semantic_services,
      description:
        "Virtual semantic PaaS/SaaS catalog for Project #2: available interfaces, projection capabilities, and live resource facets. Read-only."
    )

    tool(:project_ocel, ChatGPTCloud.DfcmMemory.MemoryRecord, :semantic_ocel,
      description:
        "OCEL-2-shaped process-evidence read model over Project #2. Conformance remains explicitly unclaimed until an independent OCEL validator executes."
    )

    tool(:project_llm_context, ChatGPTCloud.DfcmMemory.MemoryRecord, :semantic_context,
      description:
        "Bounded adjacency-aware Project #2 context optimized for LLMs: focused records, semantic neighbors, evidence-bearing identities, and truncated bodies."
    )
  end

  resources do
    resource ChatGPTCloud.DfcmMemory.MemoryRecord
  end
end
