defmodule ChatGPTCloud.DfcmMemory.Vision2030 do
  @moduledoc """
  Deterministic Vision 2030 read model over the canonical Project Two semantic graph.

  This module does not plan or execute mutations. It turns already-admitted Project
  evidence into an explicit portfolio view of autonomous software-manufacturing
  capability, evidence coverage, dependency closure, and remaining capability gaps.
  All scores are observational heuristics and never grant standing or authority.
  """

  @schema "project-two-vision-2030/v1"
  @authority "READ_ONLY_VIRTUAL_PROJECTION"

  @pillars [
    %{
      id: "deterministic-manufacture",
      label: "Deterministic manufacture",
      signals: ~w(ggen generator generated generation pack marketplace manufacture manufacturing ontology)
    },
    %{
      id: "governed-actuation",
      label: "Governed actuation",
      signals: ~w(brce authority admission receipt receipts replay standing verifier court bounded)
    },
    %{
      id: "autonomous-qualification",
      label: "Autonomous qualification",
      signals: ~w(ci test tests qualification qualify verification verify validator exact-head workflow)
    },
    %{
      id: "cloud-execution",
      label: "Cloud execution",
      signals: ~w(cloud aws azure gcp kubernetes k8s docker terraform fly deployment runtime)
    },
    %{
      id: "process-intelligence",
      label: "Process intelligence",
      signals: ~w(process ocel pm4py ex4pm provenance prov event-log conformance)
    },
    %{
      id: "semantic-interoperability",
      label: "Semantic interoperability",
      signals: ~w(semantic ontology rdf r2rml jsonld json-ld ash schema prov-o dcat skos)
    },
    %{
      id: "agent-evaluation",
      label: "Agent evaluation",
      signals: ~w(gym eval evaluation benchmark agent planner policy episode autofde)
    },
    %{
      id: "portfolio-memory",
      label: "Portfolio memory",
      signals: ~w(memory project-two frontier ledger capability receipt replay)
    }
  ]

  @dependency_predicates ~w(REQUIRES DEPENDS_ON CONSUMES_MEMORY)
  @receipt_predicates ~w(HAS_RECEIPT HAS_REPLAY)

  def project(graph, query \\ %{}) when is_map(graph) do
    query = stringify_keys(query || %{})
    minimum_evidence = query |> Map.get("minimum_evidence", 1) |> normalize_int(1) |> max(1)

    memory_nodes = Enum.filter(graph.nodes, &("MemoryRecord" in (&1.types || [])))
    repositories = Enum.filter(graph.nodes, &("Repository" in (&1.types || [])))
    commits = Enum.filter(graph.nodes, &("Commit" in (&1.types || [])))

    standing_counts =
      memory_nodes
      |> Enum.map(&get_in(&1, [:properties, :standing]))
      |> Enum.reject(&is_nil/1)
      |> Enum.frequencies()
      |> stringify_frequency_keys()

    evidence_index = build_evidence_index(graph)

    pillar_results =
      Enum.map(@pillars, fn pillar ->
        evidence = pillar_evidence(memory_nodes, pillar.signals)
        count = length(evidence)

        %{
          id: pillar.id,
          label: pillar.label,
          status: if(count >= minimum_evidence, do: "PRESENT", else: "GAP"),
          evidence_count: count,
          minimum_evidence: minimum_evidence,
          evidence: Enum.take(evidence, 25)
        }
      end)

    present = Enum.count(pillar_results, &(&1.status == "PRESENT"))
    total = length(pillar_results)

    dependency = dependency_closure(graph, memory_nodes)
    evidence = evidence_coverage(memory_nodes, evidence_index)
    frontier = frontier(memory_nodes, evidence_index, query)

    %{
      schema: @schema,
      canonical_subject: Map.get(graph, :canonical_subject, "GitHub Project v2 #2"),
      observed_at: graph.observed_at,
      authority: @authority,
      source_truncated: Map.get(graph, :source_truncated, false),
      objective: "AUTONOMIC_SOFTWARE_MANUFACTURING",
      horizon: 2030,
      interpretation:
        "Deterministic evidence projection only; not a forecast, certification, or actuation grant.",
      portfolio: %{
        memory_records: length(memory_nodes),
        repositories: length(repositories),
        commits: length(commits),
        standings: standing_counts
      },
      capability_coverage: %{
        present_pillars: present,
        total_pillars: total,
        coverage_ratio: ratio(present, total),
        pillars: pillar_results,
        gaps:
          pillar_results
          |> Enum.filter(&(&1.status == "GAP"))
          |> Enum.map(&Map.take(&1, [:id, :label, :evidence_count, :minimum_evidence]))
      },
      evidence_coverage: evidence,
      dependency_closure: dependency,
      frontier: frontier,
      admission: %{
        mutating_operations_introduced: 0,
        standing_granted: false,
        consequential_do_authority: false,
        rule: "Observation may identify gaps; only existing bounded mutation paths may act on them."
      }
    }
  end

  defp pillar_evidence(nodes, signals) do
    nodes
    |> Enum.flat_map(fn node ->
      corpus = node_corpus(node)

      matched =
        signals
        |> Enum.filter(&String.contains?(corpus, &1))
        |> Enum.uniq()

      if matched == [] do
        []
      else
        [
          %{
            id: node.id,
            label: node.label,
            memory_key: get_in(node, [:properties, :memory_key]),
            repository: get_in(node, [:properties, :repository]),
            standing: get_in(node, [:properties, :standing]),
            matched_signals: matched
          }
        ]
      end
    end)
    |> Enum.sort_by(&{to_string(&1.memory_key), &1.id})
  end

  defp node_corpus(node) do
    props = node.properties || %{}

    [
      node.label,
      node.types,
      props[:repository],
      props[:kind],
      props[:standing],
      props[:cell],
      props[:memory_key],
      props[:tags],
      props[:body]
    ]
    |> Jason.encode!()
    |> String.downcase()
  end

  defp build_evidence_index(graph) do
    Enum.reduce(graph.edges, %{}, fn edge, acc ->
      Map.update(acc, edge.source, [edge.predicate], &[edge.predicate | &1])
    end)
  end

  defp evidence_coverage(memory_nodes, evidence_index) do
    total = length(memory_nodes)

    with_standing =
      Enum.count(memory_nodes, &(get_in(&1, [:properties, :standing]) not in [nil, ""]))

    with_repository =
      Enum.count(memory_nodes, &(get_in(&1, [:properties, :repository]) not in [nil, ""]))

    with_commit =
      Enum.count(memory_nodes, fn node ->
        evidence_index
        |> Map.get(node.id, [])
        |> Enum.any?(&String.starts_with?(&1, "METADATA_"))
      end)

    with_receipt =
      Enum.count(memory_nodes, fn node ->
        predicates = Map.get(evidence_index, node.id, [])
        Enum.any?(@receipt_predicates, &(&1 in predicates))
      end)

    %{
      total_records: total,
      standing: coverage_metric(with_standing, total),
      repository_identity: coverage_metric(with_repository, total),
      commit_identity: coverage_metric(with_commit, total),
      receipt_or_replay: coverage_metric(with_receipt, total)
    }
  end

  defp dependency_closure(graph, memory_nodes) do
    memory_keys =
      memory_nodes
      |> Enum.map(&get_in(&1, [:properties, :memory_key]))
      |> Enum.reject(&is_nil/1)
      |> MapSet.new()

    node_by_id = Map.new(graph.nodes, &{&1.id, &1})

    dependencies = Enum.filter(graph.edges, &(&1.predicate in @dependency_predicates))

    unresolved =
      dependencies
      |> Enum.flat_map(fn edge ->
        target = node_by_id[edge.target]
        label = if(target, do: target.label, else: nil)

        unresolved? =
          cond do
            is_nil(target) -> true
            "MemoryKey" in (target.types || []) -> not MapSet.member?(memory_keys, label)
            true -> false
          end

        if unresolved? do
          [%{source: edge.source, predicate: edge.predicate, target: edge.target, label: label}]
        else
          []
        end
      end)
      |> Enum.sort_by(&{&1.source, &1.predicate, &1.target})

    total = length(dependencies)
    closed = max(total - length(unresolved), 0)

    %{
      dependency_edges: total,
      resolved_edges: closed,
      unresolved_edges: length(unresolved),
      closure_ratio: ratio(closed, total),
      unresolved: Enum.take(unresolved, 100)
    }
  end

  defp frontier(memory_nodes, evidence_index, query) do
    limit = query |> Map.get("frontier_limit", 20) |> normalize_int(20) |> min(100) |> max(1)

    memory_nodes
    |> Enum.map(fn node ->
      predicates = Map.get(evidence_index, node.id, [])
      standing = get_in(node, [:properties, :standing])
      repository = get_in(node, [:properties, :repository])
      key = get_in(node, [:properties, :memory_key])

      evidence_weight =
        Enum.count(predicates, fn predicate ->
          predicate in @receipt_predicates or String.starts_with?(predicate, "METADATA_")
        end)

      relation_weight = Enum.count(predicates, &(&1 in @dependency_predicates))
      standing_weight = if(standing == "ALIVE", do: 4, else: if(standing, do: 1, else: 0))
      repository_weight = if(repository, do: 1, else: 0)

      %{
        id: node.id,
        memory_key: key,
        label: node.label,
        repository: repository,
        standing: standing,
        evidence_weight: evidence_weight,
        relation_weight: relation_weight,
        observational_rank: evidence_weight + relation_weight + standing_weight + repository_weight
      }
    end)
    |> Enum.sort_by(&{-&1.observational_rank, to_string(&1.memory_key), &1.id})
    |> Enum.take(limit)
  end

  defp coverage_metric(count, total), do: %{count: count, total: total, ratio: ratio(count, total)}
  defp ratio(_count, 0), do: 0.0
  defp ratio(count, total), do: Float.round(count / total, 4)

  defp stringify_frequency_keys(frequencies),
    do: Map.new(frequencies, fn {key, value} -> {to_string(key), value} end)

  defp stringify_keys(map), do: Map.new(map, fn {key, value} -> {to_string(key), value} end)

  defp normalize_int(value, _default) when is_integer(value), do: value

  defp normalize_int(value, default) when is_binary(value) do
    case Integer.parse(value) do
      {integer, ""} -> integer
      _ -> default
    end
  end

  defp normalize_int(_, default), do: default
end
