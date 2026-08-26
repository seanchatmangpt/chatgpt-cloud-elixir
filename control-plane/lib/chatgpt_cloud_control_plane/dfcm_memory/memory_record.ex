defmodule ChatGPTCloud.DfcmMemory.MemoryRecord do
  @moduledoc """
  Ash wrapper over GitHub Project v2 `seanchatmangpt/2`, following the
  "wrap external APIs as an Ash resource" pattern. The Project is canonical;
  all semantic graph/table/triple/catalog/process/context surfaces below are
  read-only virtual projections over the same observed Project items.
  """

  use Ash.Resource,
    otp_app: :chatgpt_cloud_control_plane,
    domain: ChatGPTCloud.DfcmMemory,
    data_layer: Ash.DataLayer.Simple

  attributes do
    attribute :key, :string, primary_key?: true, allow_nil?: false, public?: true
    attribute :title, :string, public?: true
    attribute :kind, :string, public?: true
    attribute :cell, :string, public?: true
    attribute :standing, :string, public?: true
    attribute :tags, {:array, :string}, public?: true, default: []
    attribute :body, :string, public?: true
    attribute :metadata, :map, public?: true, default: %{}
    attribute :item_id, :string, public?: true
    attribute :content_id, :string, public?: true
    attribute :is_archived, :boolean, public?: true, default: false
    attribute :updated_at, :string, public?: true
  end

  actions do
    read :read do
      primary? true
      manual ChatGPTCloud.DfcmMemory.ManualRead
    end

    action :upsert_record, :map do
      description """
      Read-before-manufacture, write-after-manufacture entry point for the DfCM
      loop. Creates the memory record for `key` if it does not exist and updates
      it in place if it does. Every call goes against live Project #2.
      """

      argument :key, :string, allow_nil?: false
      argument :title, :string
      argument :kind, :string
      argument :cell, :string
      argument :standing, :string
      argument :tags, {:array, :string}, default: []
      argument :body, :string, default: ""
      argument :metadata, :map, default: %{}

      run ChatGPTCloud.DfcmMemory.UpsertRecord
    end

    action :snapshot, :map do
      description "Live Project #2 identity + item/memory-record counts. Read-only, no mutation."
      run ChatGPTCloud.DfcmMemory.Snapshot
    end

    action :project_items, {:array, :map} do
      description """
      Full-fidelity read of every item on Project #2 -- content, labels,
      assignees, and flattened custom field values. Read-only, no mutation.
      """

      argument :max_items, :integer
      argument :types, {:array, :string}
      argument :include_archived, :boolean, default: false

      run ChatGPTCloud.DfcmMemory.ProjectItems
    end

    action :semantic_project, :map do
      description "One-subject/many-views semantic bundle over Project #2."
      argument :views, {:array, :string}
      argument :query, :map, default: %{}
      argument :max_items, :integer
      argument :types, {:array, :string}
      argument :include_archived, :boolean, default: false
      argument :include_bodies, :boolean, default: true
      run ChatGPTCloud.DfcmMemory.SemanticBundle
    end

    action :semantic_graph, :map do
      description "Property graph projection over Project #2 with explicit-evidence edges only."
      argument :max_items, :integer
      argument :types, {:array, :string}
      argument :include_archived, :boolean, default: false
      argument :include_bodies, :boolean, default: true
      run ChatGPTCloud.DfcmMemory.SemanticGraph
    end

    action :semantic_graph_query, :map do
      description "Bounded filters and neighborhood traversal over the virtual Project #2 graph."
      argument :query, :map, default: %{}
      argument :max_items, :integer
      argument :types, {:array, :string}
      argument :include_archived, :boolean, default: false
      argument :include_bodies, :boolean, default: true
      run ChatGPTCloud.DfcmMemory.SemanticGraphQuery
    end

    action :semantic_tables, :map do
      description "Relational node/edge/fact rows projected from the Project #2 semantic graph."
      argument :max_items, :integer
      argument :types, {:array, :string}
      argument :include_archived, :boolean, default: false
      argument :include_bodies, :boolean, default: true
      run ChatGPTCloud.DfcmMemory.SemanticTables
    end

    action :semantic_triples, :map do
      description "RDF-shaped subject/predicate/object facts projected from Project #2."
      argument :max_items, :integer
      argument :types, {:array, :string}
      argument :include_archived, :boolean, default: false
      argument :include_bodies, :boolean, default: true
      run ChatGPTCloud.DfcmMemory.SemanticTriples
    end

    action :semantic_jsonld, :map do
      description "JSON-LD graph projection using public PROV/DCAT/DCTERMS/SKOS/FOAF/DOAP namespaces plus Project Two predicates."
      argument :max_items, :integer
      argument :types, {:array, :string}
      argument :include_archived, :boolean, default: false
      argument :include_bodies, :boolean, default: true
      run ChatGPTCloud.DfcmMemory.SemanticJsonLd
    end

    action :semantic_services, :map do
      description "Virtual PaaS/SaaS capability catalog and resource facets derived from Project #2."
      argument :max_items, :integer
      argument :types, {:array, :string}
      argument :include_archived, :boolean, default: false
      argument :include_bodies, :boolean, default: true
      run ChatGPTCloud.DfcmMemory.SemanticServices
    end

    action :semantic_ocel, :map do
      description "OCEL-2-shaped process-evidence projection; conformance is not claimed until independently validated."
      argument :max_items, :integer
      argument :types, {:array, :string}
      argument :include_archived, :boolean, default: false
      argument :include_bodies, :boolean, default: true
      run ChatGPTCloud.DfcmMemory.SemanticOcel
    end

    action :semantic_context, :map do
      description "Bounded, adjacency-aware context projection optimized for LLM consumption."
      argument :query, :map, default: %{}
      argument :max_items, :integer
      argument :types, {:array, :string}
      argument :include_archived, :boolean, default: false
      argument :include_bodies, :boolean, default: true
      run ChatGPTCloud.DfcmMemory.SemanticContext
    end
  end
end
