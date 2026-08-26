defmodule ChatGPTCloud.DfcmMemory.VirtualProjectTest do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.DfcmMemory.VirtualProject

  test "projects one subject into graph, tables, triples, catalog, process evidence and LLM context" do
    project = %{owner: "seanchatmangpt", number: 2, id: "PVT_test", title: "Project Two", url: "https://example.test/2"}

    items = [
      %{
        item_id: "PVTI_1",
        type: "DRAFT_ISSUE",
        is_archived: false,
        content_id: "DI_1",
        title: "Frontier",
        body: "encoded",
        url: nil,
        number: nil,
        repository: nil,
        state: nil,
        labels: [],
        assignees: [],
        field_values: %{"Status" => "Active"}
      },
      %{
        item_id: "PVTI_2",
        type: "ISSUE",
        is_archived: false,
        content_id: "I_2",
        title: "Consumer",
        body: "ordinary issue",
        url: "https://example.test/issues/2",
        number: 2,
        repository: "seanchatmangpt/ex4pm",
        state: "OPEN",
        labels: [%{name: "capability", color: "ffffff"}],
        assignees: [%{login: "seanchatmangpt"}],
        field_values: %{"Status" => "Todo"}
      }
    ]

    memory = [
      %{
        item_id: "PVTI_1",
        content_id: "DI_1",
        title: "Frontier",
        body: "Current frontier",
        is_archived: false,
        metadata: %{
          "key" => "dfcm/frontier/current",
          "kind" => "dfcm.frontier",
          "standing" => "ALIVE",
          "cell" => "PORTFOLIO",
          "tags" => ["dfcm", "frontier"],
          "repo" => "seanchatmangpt/ggen-marketplace",
          "head_sha" => "0123456789abcdef0123456789abcdef01234567",
          "memory_keys_consumed" => ["dfcm/ledger/current"],
          "created_at" => "2026-08-25T16:00:00Z",
          "updated_at" => "2026-08-25T17:00:00Z"
        }
      }
    ]

    graph =
      VirtualProject.build(project, items, memory,
        observed_at: "2026-08-25T17:49:00Z"
      )

    assert graph.schema == "project-two-semantic/v1"
    assert Enum.any?(graph.edges, &(&1.predicate == "CONSUMES_MEMORY"))
    assert Enum.any?(graph.nodes, &("Repository" in &1.types))
    assert Enum.any?(graph.nodes, &("Commit" in &1.types))
    assert graph.tables.nodes != []
    assert graph.triples != []
    assert graph.jsonld["@graph"] != []
    assert graph.services.model == "virtual-semantic-paas"
    assert graph.ocel.conformance == "NOT_CLAIMED_UNTIL_INDEPENDENT_OCEL_VALIDATOR_EXECUTES"

    context = VirtualProject.context(graph, %{"types" => ["MemoryRecord"], "max_body_chars" => 7})
    assert context.returned_records == 1
    assert hd(context.records).body == "Current"
  end

  test "free prose is retained as a fact but is not promoted into a dependency edge" do
    project = %{owner: "seanchatmangpt", number: 2, id: "PVT_test", title: "Project Two", url: nil}
    item = %{item_id: "I", type: "DRAFT_ISSUE", is_archived: false, content_id: "D", title: "x", body: "", url: nil, number: nil, repository: nil, state: nil, labels: [], assignees: [], field_values: %{}}
    memory = %{item_id: "I", content_id: "D", title: "x", body: "", is_archived: false, metadata: %{"key" => "dfcm/x", "body_note" => "maybe depends on something"}}

    graph = VirtualProject.build(project, [item], [memory], observed_at: "2026-08-25T17:49:00Z")

    refute Enum.any?(graph.edges, &(&1.predicate == "DEPENDS_ON"))
    assert Enum.any?(graph.facts, &(&1.predicate == "metadata.body_note"))
  end
end
