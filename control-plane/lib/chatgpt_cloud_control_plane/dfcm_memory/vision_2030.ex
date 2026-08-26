defmodule ChatGPTCloud.DfcmMemory.Vision2030 do
  @moduledoc """
  Deterministic Vision 2030 read model over the canonical Project Two semantic graph.

  This module does not plan or execute mutations. It turns already-admitted Project
  evidence into an explicit portfolio view of autonomous software-manufacturing
  capability, evidence diversity, productive capital, combinatorial option space,
  dependency closure, and remaining capability gaps. All scores are observational
  heuristics and never grant standing or authority.
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

  @capital_classes [
    %{
      id: "generative-capital",
      signals: ~w(ggen generator generation pack marketplace manufacture manufacturing)
    },
    %{
      id: "governance-capital",
      signals: ~w(brce authority admission receipt replay verifier court standing)
    },
    %{
      id: "qualification-capital",
      signals: ~w(ci test qualification verification validator exact-head workflow)
    },
    %{
      id: "semantic-capital",
      signals: ~w(ontology semantic rdf r2rml jsonld prov-o dcat skos ocel)
    },
    %{
      id: "execution-capital",
      signals: ~w(cloud aws azure gcp kubernetes docker terraform runtime deployment)
    },
    %{
      id: "evaluation-capital",
      signals: ~w(gym eval evaluation benchmark planner policy episode autofde)
    },
    %{
      id: "memory-capital",
      signals: ~w(memory project-two frontier ledger capability)
    }
  ]

  @dependency_predicates ~w(REQUIRES DEPENDS_ON CONSUMES_MEMORY)
  @receipt_predicates ~w(HAS_RECEIPT HAS_REPLAY)

  def project(graph, query \\ %{}) when is_map(graph) do
    query = stringify_keys(query || %{})
    minimum_evidence = query |> Map.get("minimum_evidence", 1) |> normalize_int(1) |> max(1)

    minimum_domains =
      query
      |> Map.get("minimum_domains", 1)
      |> normalize_int(1)
      |> min(10)
      |> max(1)

    minimum_receipt_ratio =
      query
      |> Map.get("minimum_receipt_ratio", 0.0)
      |> normalize_ratio(0.0)

    memory_nodes = Enum.filter(graph.nodes, &("MemoryRecord" in (&1.types || [])))
    repositories = Enum.filter(graph.nodes, &("Repository" in (&1.types || [])))
    commits = Enum.filter(graph.nodes, &("Commit" in (&1.types || [])))

    standing_counts =
      memory_nodes
      |> Enum.map(&get_in(&1, [:properties, :standing]))
      |> Enum.reject(&(&1 in [nil, ""]))
      |> Enum.frequencies()
      |> stringify_frequency_keys()

    evidence_index = build_evidence_index(graph)

    pillar_results =
      Enum.map(@pillars, fn pillar ->
        evidence = pillar_evidence(memory_nodes, pillar.signals)
        domains = evidence |> Enum.map(&evidence_domain/1) |> Enum.uniq() |> Enum.sort()
        count = length(evidence)

        falsifiers =
          [
            if(count < minimum_evidence, do: "EVIDENCE_SHORTFALL"),
            if(length(domains) < minimum_domains, do: "DOMAIN_DIVERSITY_SHORTFALL")
          ]
          |> Enum.reject(&is_nil/1)

        %{
          id: pillar.id,
          label: pillar.label,
          status: if(falsifiers == [], do: "PRESENT", else: "GAP"),
          evidence_count: count,
          minimum_evidence: minimum_evidence,
          evidence_domains: domains,
          domain_count: length(domains),
          minimum_domains: minimum_domains,
          falsifiers: falsifiers,
          evidence: Enum.take(evidence, 25)
        }
      end)

    present = Enum.count(pillar_results, &(&1.status == "PRESENT"))
    total = length(pillar_results)

    dependency = dependency_closure(graph, memory_nodes)
    evidence = evidence_coverage(memory_nodes, evidence_index)
    combinatorial = combinatorial_option_space(memory_nodes)
    capital = manufacturing_capital(memory_nodes, evidence_index)
    maximalist_frontier = maximalist_frontier(pillar_results, combinatorial)

    autonomy =
      autonomy_envelope(
        graph,
        pillar_results,
        dependency,
        evidence,
        capital,
        minimum_receipt_ratio
      )

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
          |> Enum.map(
            &Map.take(&1, [
              :id,
              :label,
              :evidence_count,
              :minimum_evidence,
              :domain_count,
              :minimum_domains,
              :falsifiers
            ])
          )
      },
      evidence_coverage: evidence,
      dependency_closure: dependency,
      manufacturing_capital: capital,
      combinatorial_option_space: combinatorial,
      maximalist_frontier: maximalist_frontier,
      autonomy_envelope: autonomy,
      frontier: frontier(memory_nodes, evidence_index, query),
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
        |> Enum.sort()

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
    |> Enum.sort_by(&{to_string(&1.memory_key), to_string(&1.id)})
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

  defp evidence_domain(item) do
    case item.repository do
      value when value in [nil, ""] -> "project-memory"
      value -> to_string(value)
    end
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
      |> Enum.sort_by(&{to_string(&1.source), to_string(&1.predicate), to_string(&1.target)})

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

  defp combinatorial_option_space(memory_nodes) do
    {observed_pairs, cross_pillar_records} =
      Enum.reduce(memory_nodes, {MapSet.new(), 0}, fn node, {pairs, cross_count} ->
        corpus = node_corpus(node)

        matched =
          @pillars
          |> Enum.filter(fn pillar -> Enum.any?(pillar.signals, &String.contains?(corpus, &1)) end)
          |> Enum.map(& &1.id)
          |> Enum.sort()

        node_pairs =
          matched
          |> Enum.with_index()
          |> Enum.flat_map(fn {left, index} ->
            matched
            |> Enum.drop(index + 1)
            |> Enum.map(&{left, &1})
          end)

        {
          Enum.reduce(node_pairs, pairs, &MapSet.put(&2, &1)),
          if(length(matched) >= 2, do: cross_count + 1, else: cross_count)
        }
      end)

    possible_pairings = div(length(@pillars) * (length(@pillars) - 1), 2)
    pairings = observed_pairs |> Enum.sort() |> Enum.map(fn {left, right} -> [left, right] end)

    %{
      possible_pairings: possible_pairings,
      observed_pairings: length(pairings),
      pairing_coverage_ratio: ratio(length(pairings), possible_pairings),
      cross_pillar_records: cross_pillar_records,
      pairings: pairings,
      interpretation:
        "Observed co-occurrence topology only; pairings are not causal claims or effort estimates."
    }
  end

  defp manufacturing_capital(memory_nodes, evidence_index) do
    capital_records =
      Enum.flat_map(memory_nodes, fn node ->
        corpus = node_corpus(node)

        matched_classes =
          @capital_classes
          |> Enum.filter(fn capital_class ->
            Enum.any?(capital_class.signals, &String.contains?(corpus, &1))
          end)
          |> Enum.map(& &1.id)
          |> Enum.sort()

        if matched_classes == [] do
          []
        else
          standing = get_in(node, [:properties, :standing])
          repository = get_in(node, [:properties, :repository])
          memory_key = get_in(node, [:properties, :memory_key])
          predicates = Map.get(evidence_index, node.id, [])
          has_receipt = Enum.any?(@receipt_predicates, &(&1 in predicates))

          [
            %{
              id: node.id,
              memory_key: memory_key,
              repository: repository,
              standing: standing,
              classes: matched_classes,
              class_count: length(matched_classes),
              has_receipt_or_replay: has_receipt,
              qualified_reusable_capital: standing == "ALIVE" and has_receipt
            }
          ]
        end
      end)

    qualified = Enum.filter(capital_records, & &1.qualified_reusable_capital)

    unqualified =
      capital_records
      |> Enum.reject(& &1.qualified_reusable_capital)
      |> Enum.sort_by(fn record ->
        {
          -record.class_count,
          if(record.has_receipt_or_replay, do: 1, else: 0),
          to_string(record.memory_key),
          to_string(record.id)
        }
      end)

    by_class =
      capital_records
      |> Enum.flat_map(& &1.classes)
      |> Enum.frequencies()
      |> Enum.sort()
      |> Map.new()

    %{
      capital_records: length(capital_records),
      portfolio_records: length(memory_nodes),
      capital_ratio: ratio(length(capital_records), length(memory_nodes)),
      qualified_reusable_capital: length(qualified),
      qualified_capital_ratio: ratio(length(qualified), length(capital_records)),
      by_class: by_class,
      unqualified_capital_frontier: Enum.take(unqualified, 50),
      interpretation:
        "Capital means reusable productive machinery evidenced in Project memory; it is not financial-accounting capitalization."
    }
  end

  defp maximalist_frontier(pillar_results, combinatorial) do
    observed_pairs =
      combinatorial.pairings
      |> Enum.map(fn pair -> pair |> Enum.sort() |> List.to_tuple() end)
      |> MapSet.new()

    pillar_ids = Enum.map(pillar_results, & &1.id)

    pillar_results
    |> Enum.filter(&(&1.status == "GAP"))
    |> Enum.map(fn pillar ->
      unrealized =
        pillar_ids
        |> Enum.reject(&(&1 == pillar.id))
        |> Enum.reject(fn other ->
          pair = [pillar.id, other] |> Enum.sort() |> List.to_tuple()
          MapSet.member?(observed_pairs, pair)
        end)
        |> Enum.sort()

      evidence_shortfall = max(pillar.minimum_evidence - pillar.evidence_count, 0)
      domain_shortfall = max(pillar.minimum_domains - pillar.domain_count, 0)

      %{
        id: pillar.id,
        label: pillar.label,
        unrealized_pairing_count: length(unrealized),
        unrealized_pairings_with: unrealized,
        evidence_shortfall: evidence_shortfall,
        domain_shortfall: domain_shortfall,
        option_surface_score: length(unrealized) + evidence_shortfall + domain_shortfall,
        falsifiers: pillar.falsifiers
      }
    end)
    |> Enum.sort_by(&{-&1.option_surface_score, -&1.unrealized_pairing_count, &1.id})
  end

  defp autonomy_envelope(
         graph,
         pillar_results,
         dependency,
         evidence,
         capital,
         minimum_receipt_ratio
       ) do
    capability_gaps =
      pillar_results
      |> Enum.filter(&(&1.status == "GAP"))
      |> Enum.map(& &1.id)

    falsifiers =
      [
        if(Map.get(graph, :source_truncated, false), do: "SOURCE_TRUNCATED"),
        if(capability_gaps != [], do: "CAPABILITY_GAPS"),
        if(dependency.unresolved_edges > 0, do: "UNRESOLVED_DEPENDENCIES"),
        if(evidence.receipt_or_replay.ratio < minimum_receipt_ratio,
          do: "RECEIPT_COVERAGE_SHORTFALL"
        )
      ]
      |> Enum.reject(&is_nil/1)

    closed = falsifiers == []

    %{
      status: if(closed, do: "CLOSED", else: "OPEN"),
      structural_phase: if(closed, do: "INTEGRATED_AUTONOMIC_STACK", else: "ASSEMBLY_IN_PROGRESS"),
      falsifiers: falsifiers,
      capability_gaps: capability_gaps,
      minimum_receipt_ratio: minimum_receipt_ratio,
      observed_receipt_ratio: evidence.receipt_or_replay.ratio,
      qualified_reusable_capital: capital.qualified_reusable_capital,
      standing: "OBSERVATIONAL_ONLY",
      interpretation:
        "Envelope closure is a deterministic structural condition, not production certification or authority to act."
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

      standing_weight =
        cond do
          standing == "ALIVE" -> 4
          standing in [nil, ""] -> 0
          true -> 1
        end

      repository_weight = if(repository in [nil, ""], do: 0, else: 1)

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
    |> Enum.sort_by(&{-&1.observational_rank, to_string(&1.memory_key), to_string(&1.id)})
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

  defp normalize_ratio(value, _default) when is_integer(value) or is_float(value) do
    value
    |> max(0.0)
    |> min(1.0)
    |> Float.round(4)
  end

  defp normalize_ratio(value, default) when is_binary(value) do
    case Float.parse(value) do
      {number, ""} -> normalize_ratio(number, default)
      _ -> default
    end
  end

  defp normalize_ratio(_, default), do: default
end
