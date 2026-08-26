defmodule ChatGPTCloud.DfcmMemory.Vision2030Test do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.DfcmMemory.{VirtualProject, Vision2030}

  test "projects autonomous manufacturing capability, capital, and option space without granting authority" do
    project = %{
      owner: "seanchatmangpt",
      number: 2,
      id: "PVT_test",
      title: "Project Two",
      url: "https://example.test/2"
    }

    items = [
      item("A", "Manufacturing frontier"),
      item("B", "Cloud gym qualification"),
      item("C", "Unresolved consumer")
    ]

    memory = [
      memory("A", %{
        "key" => "project/vision/manufacturing",
        "standing" => "ALIVE",
        "repo" => "seanchatmangpt/ggen-marketplace",
        "tags" => ["ggen", "ontology", "receipt", "semantic"],
        "head_sha" => "0123456789abcdef0123456789abcdef01234567",
        "receipt" => "dfcm/receipt/manufacturing"
      }),
      memory("B", %{
        "key" => "project/vision/cloud-gym",
        "standing" => "PARTIAL_ALIVE",
        "repo" => "seanchatmangpt/gymact",
        "tags" => ["cloud", "aws", "azure", "gcp", "gym", "benchmark", "ci"],
        "requires" => "project/vision/manufacturing"
      }),
      memory("C", %{
        "key" => "project/vision/consumer",
        "standing" => "UNKNOWN",
        "repo" => "seanchatmangpt/autofde",
        "dependencies" => "project/vision/missing-capability"
      })
    ]

    graph = VirtualProject.build(project, items, memory, observed_at: "2026-08-26T02:00:00Z")
    projection = Vision2030.project(graph)

    assert projection.schema == "project-two-vision-2030/v1"
    assert projection.objective == "AUTONOMIC_SOFTWARE_MANUFACTURING"
    assert projection.horizon == 2030
    assert projection.authority == "READ_ONLY_VIRTUAL_PROJECTION"
    assert projection.admission.mutating_operations_introduced == 0
    refute projection.admission.standing_granted
    refute projection.admission.consequential_do_authority

    assert projection.portfolio.memory_records == 3
    assert projection.portfolio.repositories >= 3
    assert projection.evidence_coverage.standing.count == 3
    assert projection.evidence_coverage.commit_identity.count == 1
    assert projection.evidence_coverage.receipt_or_replay.count == 1

    assert projection.dependency_closure.dependency_edges == 2
    assert projection.dependency_closure.resolved_edges == 1
    assert projection.dependency_closure.unresolved_edges == 1
    assert projection.dependency_closure.closure_ratio == 0.5

    assert Enum.any?(
             projection.capability_coverage.pillars,
             &(&1.id == "deterministic-manufacture" and &1.status == "PRESENT")
           )

    assert Enum.any?(
             projection.capability_coverage.pillars,
             &(&1.id == "agent-evaluation" and &1.status == "PRESENT")
           )

    assert Enum.any?(
             projection.frontier,
             &(&1.memory_key == "project/vision/manufacturing")
           )

    assert projection.manufacturing_capital.capital_records >= 2
    assert projection.manufacturing_capital.qualified_reusable_capital == 1
    assert projection.manufacturing_capital.capital_ratio > 0.0
    assert map_size(projection.manufacturing_capital.by_class) > 0

    assert projection.combinatorial_option_space.possible_pairings == 28
    assert projection.combinatorial_option_space.observed_pairings > 0
    assert projection.combinatorial_option_space.cross_pillar_records > 0

    assert projection.autonomy_envelope.status == "OPEN"
    assert projection.autonomy_envelope.structural_phase == "ASSEMBLY_IN_PROGRESS"
    assert "UNRESOLVED_DEPENDENCIES" in projection.autonomy_envelope.falsifiers
    assert projection.maximalist_frontier != []
  end

  test "minimum evidence makes capability admission explicit instead of implied" do
    project = %{
      owner: "seanchatmangpt",
      number: 2,
      id: "PVT_test",
      title: "Project Two",
      url: nil
    }

    graph =
      VirtualProject.build(
        project,
        [item("A", "One semantic record")],
        [
          memory("A", %{
            "key" => "project/vision/semantic",
            "standing" => "ALIVE",
            "tags" => ["semantic", "ontology", "rdf"]
          })
        ],
        observed_at: "2026-08-26T02:00:00Z"
      )

    projection = Vision2030.project(graph, %{"minimum_evidence" => 2})

    semantic =
      Enum.find(projection.capability_coverage.pillars, &(&1.id == "semantic-interoperability"))

    assert semantic.evidence_count == 1
    assert semantic.minimum_evidence == 2
    assert semantic.status == "GAP"
    assert "EVIDENCE_SHORTFALL" in semantic.falsifiers
    assert Enum.any?(projection.capability_coverage.gaps, &(&1.id == "semantic-interoperability"))
  end

  test "domain diversity prevents a single evidence domain from Goodharting a pillar" do
    project = %{
      owner: "seanchatmangpt",
      number: 2,
      id: "PVT_test",
      title: "Project Two",
      url: nil
    }

    graph =
      VirtualProject.build(
        project,
        [item("A", "Manufacturing")],
        [
          memory("A", %{
            "key" => "project/vision/manufacturing",
            "standing" => "ALIVE",
            "repo" => "seanchatmangpt/ggen-marketplace",
            "tags" => ["ggen", "generator", "pack", "manufacturing"]
          })
        ],
        observed_at: "2026-08-26T02:00:00Z"
      )

    projection = Vision2030.project(graph, %{"minimum_domains" => 2})

    deterministic =
      Enum.find(projection.capability_coverage.pillars, &(&1.id == "deterministic-manufacture"))

    assert deterministic.domain_count == 1
    assert deterministic.minimum_domains == 2
    assert deterministic.status == "GAP"
    assert "DOMAIN_DIVERSITY_SHORTFALL" in deterministic.falsifiers
  end

  test "closed autonomy envelope is structural and never grants actuation authority" do
    project = %{
      owner: "seanchatmangpt",
      number: 2,
      id: "PVT_test",
      title: "Project Two",
      url: nil
    }

    graph =
      VirtualProject.build(
        project,
        [item("Z", "Integrated autonomic stack")],
        [
          memory("Z", %{
            "key" => "project/vision/integrated-stack",
            "standing" => "ALIVE",
            "repo" => "seanchatmangpt/autonomic-stack",
            "tags" => ["ggen", "receipt", "ci", "cloud", "process", "semantic", "gym", "memory"],
            "head_sha" => "fedcba9876543210fedcba9876543210fedcba98",
            "receipt" => "dfcm/receipt/integrated-stack"
          })
        ],
        observed_at: "2026-08-26T03:00:00Z"
      )

    projection = Vision2030.project(graph, %{"minimum_receipt_ratio" => 1.0})

    assert projection.capability_coverage.present_pillars == 8
    assert projection.autonomy_envelope.status == "CLOSED"
    assert projection.autonomy_envelope.structural_phase == "INTEGRATED_AUTONOMIC_STACK"
    assert projection.autonomy_envelope.falsifiers == []
    assert projection.autonomy_envelope.standing == "OBSERVATIONAL_ONLY"
    refute projection.admission.standing_granted
    refute projection.admission.consequential_do_authority
  end

  defp item(id, title) do
    %{
      item_id: id,
      type: "DRAFT_ISSUE",
      is_archived: false,
      content_id: "D_#{id}",
      title: title,
      body: "",
      url: nil,
      number: nil,
      repository: nil,
      state: nil,
      labels: [],
      assignees: [],
      field_values: %{}
    }
  end

  defp memory(id, metadata) do
    %{
      item_id: id,
      content_id: "D_#{id}",
      title: "memory #{id}",
      body: "",
      is_archived: false,
      metadata: metadata
    }
  end
end
