defmodule ChatGPTCloud.DfcmMemory.VirtualProject do
  @moduledoc """
  Read-only semantic virtualization of GitHub Project v2 #2.

  The GitHub Project remains canonical. This module performs an AshR2RML-style
  projection over the same admitted subject into property-graph, fact/triple,
  tabular, service-catalog, OCEL-shaped, and compact LLM-context views. It has no
  mutation or actuation path.
  """

  alias ChatGPTCloud.DfcmMemory.GithubProjectClient

  @schema "project-two-semantic/v1"
  @base "urn:project-two:"
  @capabilities [
    %{
      name: "memory-kv",
      operations:
        ~w(memory.create memory.read memory.update memory.upsert memory.query memory.archive memory.delete)
    },
    %{name: "project-object-store", operations: ~w(project.snapshot project.items)},
    %{name: "property-graph", operations: ~w(project.graph project.graph.query)},
    %{name: "semantic-facts", operations: ~w(project.triples)},
    %{name: "json-ld", operations: ~w(project.jsonld)},
    %{name: "relational-projection", operations: ~w(project.tables)},
    %{name: "service-catalog", operations: ~w(project.services)},
    %{name: "process-evidence", operations: ~w(project.ocel)},
    %{name: "llm-context", operations: ~w(project.context)}
  ]

  @reference_relations %{
    "memory_keys_consumed" => "CONSUMES_MEMORY",
    "memory_keys_updated" => "UPDATES_MEMORY",
    "memory_created" => "CREATES_MEMORY",
    "memory_keys_created" => "CREATES_MEMORY",
    "requires" => "REQUIRES",
    "dependencies" => "DEPENDS_ON",
    "dependency_keys" => "DEPENDS_ON",
    "unlocks" => "UNLOCKS",
    "supersedes" => "SUPERSEDES",
    "derived_from" => "DERIVED_FROM",
    "receipts" => "HAS_RECEIPT",
    "receipt" => "HAS_RECEIPT",
    "replay" => "HAS_REPLAY"
  }

  def project(opts \\ []) do
    max_items = Keyword.get(opts, :max_items, 5000) |> min(5000) |> max(1)
    include_archived = Keyword.get(opts, :include_archived, false)
    types = Keyword.get(opts, :types)
    include_bodies = Keyword.get(opts, :include_bodies, true)

    item_opts =
      [max_items: max_items, include_archived: include_archived, types: types]
      |> Enum.reject(fn {_k, value} -> is_nil(value) end)

    with {:ok, project} <- GithubProjectClient.resolve_project(),
         {:ok, items} <- GithubProjectClient.project_items(item_opts),
         {:ok, {memory_records, memory_truncated}} <-
           GithubProjectClient.memory_items(include_archived, max_items) do
      {:ok,
       build(project, items, memory_records,
         include_bodies: include_bodies,
         source_truncated: memory_truncated
       )}
    end
  end

  def build(project, items, memory_records, opts \\ []) do
    observed_at = Keyword.get_lazy(opts, :observed_at, &now/0)
    include_bodies = Keyword.get(opts, :include_bodies, true)
    source_truncated = Keyword.get(opts, :source_truncated, false)
    memory_by_item = Map.new(memory_records, &{&1.item_id, &1})

    state = %{
      nodes: %{},
      edges: %{},
      facts: [],
      project: project,
      observed_at: observed_at
    }

    project_key = "#{project.owner}/#{project.number}"
    project_id = urn("project", project_key)

    state =
      put_node(
        state,
        project_id,
        ["Project", "prov:Entity", "dcat:Dataset"],
        project.title || project_key,
        %{
          owner: project.owner,
          number: project.number,
          node_id: project.id,
          url: project.url
        }
      )

    state =
      Enum.reduce(items, state, fn item, acc ->
        add_item(acc, project_id, item, Map.get(memory_by_item, item.item_id), include_bodies)
      end)

    nodes = state.nodes |> Map.values() |> Enum.sort_by(& &1.id)

    edges =
      state.edges |> Map.values() |> Enum.sort_by(&{&1.source, &1.predicate, &1.target, &1.id})

    facts = Enum.sort_by(state.facts, &{&1.subject, &1.predicate, inspect(&1.value)})

    graph = %{
      schema: @schema,
      project: project,
      observed_at: observed_at,
      canonical_subject: "GitHub Project v2 #2",
      authority: "READ_ONLY_VIRTUAL_PROJECTION",
      source_truncated: source_truncated,
      nodes: nodes,
      edges: edges,
      facts: facts
    }

    graph
    |> Map.put(:stats, stats(graph))
    |> Map.put(:tables, tables(graph))
    |> Map.put(:triples, triples(graph))
    |> Map.put(:jsonld, jsonld(graph))
    |> Map.put(:services, services(graph))
    |> Map.put(:ocel, ocel(graph))
  end

  def view(graph, "graph", _query),
    do:
      Map.take(graph, [
        :schema,
        :project,
        :observed_at,
        :canonical_subject,
        :authority,
        :source_truncated,
        :nodes,
        :edges,
        :facts,
        :stats
      ])

  def view(graph, "tables", _query), do: envelope(graph, %{tables: graph.tables})
  def view(graph, "triples", _query), do: envelope(graph, %{triples: graph.triples})
  def view(graph, "jsonld", _query), do: envelope(graph, %{jsonld: graph.jsonld})
  def view(graph, "services", _query), do: envelope(graph, graph.services)
  def view(graph, "ocel", _query), do: envelope(graph, %{ocel: graph.ocel})
  def view(graph, "context", query), do: context(graph, query || %{})
  def view(graph, "query", query), do: query(graph, query || %{}) |> then(&envelope(graph, &1))

  def view(_graph, other, _query),
    do: {:error, "REFUSED[UNSUPPORTED_SEMANTIC_VIEW]: #{inspect(other)}"}

  def semantic(graph, views, query \\ %{}) do
    views =
      if is_list(views) and views != [],
        do: views,
        else: ~w(graph tables triples jsonld services ocel context)

    Enum.reduce_while(views, envelope(graph, %{views: views}), fn name, acc ->
      case view(graph, to_string(name), query) do
        {:error, reason} -> {:halt, {:error, reason}}
        result -> {:cont, Map.put(acc, String.to_atom(to_string(name)), strip_envelope(result))}
      end
    end)
  end

  def query(graph, query) do
    text = query_value(query, "text", "") |> to_string() |> String.downcase()
    types = query_list(query, "types") |> MapSet.new()
    repository = query_value(query, "repository", nil)
    kind = query_value(query, "kind", nil)
    standing = query_value(query, "standing", nil)
    tags = query_list(query, "tags") |> MapSet.new()
    node_ids = query_list(query, "node_ids") |> MapSet.new()
    predicates = query_list(query, "predicates") |> MapSet.new()
    limit = query_value(query, "limit", 500) |> normalize_int(500) |> min(5000) |> max(1)

    selected =
      graph.nodes
      |> Enum.filter(fn node ->
        props = node.properties || %{}

        (MapSet.size(node_ids) == 0 or MapSet.member?(node_ids, node.id)) and
          (MapSet.size(types) == 0 or not MapSet.disjoint?(types, MapSet.new(node.types || []))) and
          (is_nil(repository) or props[:repository] == repository or props[:name] == repository) and
          (is_nil(kind) or props[:kind] == kind) and
          (is_nil(standing) or props[:standing] == standing) and
          (MapSet.size(tags) == 0 or MapSet.subset?(tags, MapSet.new(props[:tags] || []))) and
          (text == "" or String.contains?(String.downcase(Jason.encode!(node)), text))
      end)
      |> Map.new(&{&1.id, &1})

    selected = expand_neighbors(graph, selected, query, predicates)
    all_count = map_size(selected)
    nodes = selected |> Map.values() |> Enum.sort_by(& &1.id) |> Enum.take(limit)
    ids = MapSet.new(nodes, & &1.id)

    edges =
      graph.edges
      |> Enum.filter(fn edge ->
        MapSet.member?(ids, edge.source) and MapSet.member?(ids, edge.target) and
          (MapSet.size(predicates) == 0 or MapSet.member?(predicates, edge.predicate))
      end)
      |> Enum.take(limit * 10)

    facts = graph.facts |> Enum.filter(&MapSet.member?(ids, &1.subject)) |> Enum.take(limit * 20)

    %{
      query: query,
      nodes: nodes,
      edges: edges,
      facts: facts,
      matched_nodes: all_count,
      returned_nodes: length(nodes),
      truncated: all_count > length(nodes)
    }
  end

  def context(graph, query) do
    query = Map.put_new(stringify_keys(query || %{}), "limit", 100)
    result = query(graph, query)

    max_body =
      query_value(query, "max_body_chars", 1200) |> normalize_int(1200) |> min(20_000) |> max(0)

    adjacency =
      Enum.reduce(result.edges, %{}, fn edge, acc ->
        acc
        |> Map.update(
          edge.source,
          [%{predicate: edge.predicate, target: edge.target}],
          &[%{predicate: edge.predicate, target: edge.target} | &1]
        )
        |> Map.update(
          edge.target,
          [%{predicate: "INVERSE_#{edge.predicate}", target: edge.source}],
          &[%{predicate: "INVERSE_#{edge.predicate}", target: edge.source} | &1]
        )
      end)

    records =
      Enum.map(result.nodes, fn node ->
        props = node.properties || %{}
        body = props[:body] || ""

        %{
          id: node.id,
          label: node.label,
          types: node.types,
          repository: props[:repository],
          kind: props[:kind],
          standing: props[:standing],
          cell: props[:cell],
          memory_key: props[:memory_key],
          tags: props[:tags] || [],
          body: if(max_body == 0, do: nil, else: String.slice(body, 0, max_body)),
          relations:
            adjacency
            |> Map.get(node.id, [])
            |> Enum.sort_by(&{&1.predicate, &1.target})
            |> Enum.take(100)
        }
      end)

    envelope(graph, %{
      schema: "project-two-llm-context/v1",
      query: query,
      records: records,
      returned_records: length(records),
      truncated: result.truncated
    })
  end

  defp add_item(state, project_id, item, memory, include_bodies) do
    node_id = urn("item", item.item_id)
    metadata = if(memory, do: memory.metadata || %{}, else: %{})
    key = metadata["key"]
    kind = metadata["kind"]
    standing = metadata["standing"]
    cell = metadata["cell"]

    tags =
      metadata
      |> Map.get("tags", [])
      |> listify()
      |> Enum.map(&to_string/1)
      |> Enum.uniq()
      |> Enum.sort()

    types =
      ["ProjectItem", "prov:Entity", item.type || "UNKNOWN"] ++
        if(memory, do: ["MemoryRecord"] ++ if(kind, do: ["kind:#{kind}"], else: []), else: [])

    props = %{
      item_id: item.item_id,
      content_id: item.content_id,
      title: item.title || "",
      url: item.url,
      number: item.number,
      repository: item.repository,
      state: item.state,
      is_archived: item.is_archived,
      field_values: item.field_values || %{},
      memory_key: key,
      kind: kind,
      standing: standing,
      cell: cell,
      tags: tags,
      body:
        if(include_bodies,
          do: if(memory, do: memory.body || "", else: item.body || ""),
          else: nil
        )
    }

    state = put_node(state, node_id, types, item.title || key || item.item_id, props)
    state = put_edge(state, project_id, "CONTAINS", node_id, "project-item:#{item.item_id}")

    state =
      Enum.reduce(item.field_values || %{}, state, fn {field, value}, acc ->
        put_fact(acc, node_id, "field.#{field}", value, "project-field:#{field}")
      end)

    repository = item.repository || metadata["repo"]

    state =
      if repository do
        repo_id = urn("repository", to_string(repository))

        state
        |> put_node(
          repo_id,
          ["Repository", "doap:Repository", "schema:SoftwareSourceCode"],
          to_string(repository),
          %{name: to_string(repository)}
        )
        |> put_edge(node_id, "BELONGS_TO_REPOSITORY", repo_id, "explicit repository field")
      else
        state
      end

    state =
      Enum.reduce(item.labels || [], state, fn label, acc ->
        name = label[:name] || label["name"]

        if name in [nil, ""] do
          acc
        else
          label_id = urn("label", to_string(name))

          acc
          |> put_node(label_id, ["Label", "skos:Concept"], to_string(name), %{
            name: name,
            color: label[:color] || label["color"]
          })
          |> put_edge(node_id, "HAS_LABEL", label_id, "GitHub label")
        end
      end)

    state =
      Enum.reduce(item.assignees || [], state, fn assignee, acc ->
        login = if(is_map(assignee), do: assignee[:login] || assignee["login"], else: assignee)

        if login in [nil, ""] do
          acc
        else
          actor_id = urn("actor", to_string(login))

          acc
          |> put_node(actor_id, ["Actor", "foaf:Agent"], to_string(login), %{login: login})
          |> put_edge(node_id, "ASSIGNED_TO", actor_id, "GitHub assignee")
        end
      end)

    if memory do
      state
      |> add_memory_identity(node_id, key, tags)
      |> add_metadata_facts(node_id, metadata)
      |> add_reference_edges(node_id, metadata)
      |> add_commit_edges(node_id, metadata)
    else
      state
    end
  end

  defp add_memory_identity(state, node_id, key, tags) do
    state =
      if key do
        memory_id = urn("memory", to_string(key))

        state
        |> put_node(memory_id, ["MemoryKey", "prov:Entity"], to_string(key), %{key: key})
        |> put_edge(node_id, "HAS_MEMORY_KEY", memory_id, "memory marker metadata")
      else
        state
      end

    Enum.reduce(tags, state, fn tag, acc ->
      tag_id = urn("tag", tag)

      acc
      |> put_node(tag_id, ["Tag", "skos:Concept"], tag, %{name: tag})
      |> put_edge(node_id, "TAGGED_WITH", tag_id, "memory metadata tags")
    end)
  end

  defp add_metadata_facts(state, node_id, metadata) do
    metadata
    |> flatten("metadata")
    |> Enum.reduce(state, fn {path, value}, acc ->
      put_fact(acc, node_id, path, value, "memory marker metadata")
    end)
  end

  defp add_reference_edges(state, node_id, metadata) do
    Enum.reduce(@reference_relations, state, fn {key, predicate}, acc ->
      metadata
      |> Map.get(key)
      |> listify()
      |> Enum.reduce(acc, fn value, inner ->
        case reference_target(value, key) do
          nil ->
            inner

          {target_id, target_type} ->
            inner
            |> put_node(target_id, [target_type, "prov:Entity"], to_string(value), %{value: value})
            |> put_edge(node_id, predicate, target_id, "metadata.#{key}", %{metadata_key: key})
        end
      end)
    end)
  end

  defp add_commit_edges(state, node_id, metadata) do
    Enum.reduce(metadata, state, fn {key, value}, acc ->
      key_s = to_string(key)

      if is_binary(value) and sha?(value) and
           Enum.any?(
             ~w(sha head base commit merge candidate),
             &String.contains?(String.downcase(key_s), &1)
           ) do
        commit_id = urn("commit", String.downcase(value))

        acc
        |> put_node(commit_id, ["Commit", "prov:Entity"], String.slice(value, 0, 12), %{
          sha: String.downcase(value)
        })
        |> put_edge(node_id, metadata_predicate(key_s), commit_id, "metadata.#{key_s}")
      else
        acc
      end
    end)
  end

  defp expand_neighbors(graph, selected, query, predicates) do
    neighbor_ids = query_list(query, "neighbors_of") |> MapSet.new()

    if MapSet.size(neighbor_ids) == 0 do
      selected
    else
      depth = query_value(query, "depth", 1) |> normalize_int(1) |> min(5) |> max(0)
      direction = query_value(query, "direction", "both") |> to_string() |> String.downcase()

      adjacency =
        Enum.reduce(graph.edges, %{}, fn edge, acc ->
          if MapSet.size(predicates) > 0 and not MapSet.member?(predicates, edge.predicate) do
            acc
          else
            acc =
              if direction in ["both", "out"],
                do: Map.update(acc, edge.source, [edge.target], &[edge.target | &1]),
                else: acc

            if direction in ["both", "in"],
              do: Map.update(acc, edge.target, [edge.source], &[edge.source | &1]),
              else: acc
          end
        end)

      seen = bfs(adjacency, MapSet.to_list(neighbor_ids), depth)

      has_filters =
        Enum.any?(~w(text types repository kind standing tags node_ids), fn key ->
          query_value(query, key, nil) not in [nil, "", []]
        end)

      ids =
        if has_filters, do: MapSet.intersection(MapSet.new(Map.keys(selected)), seen), else: seen

      all_nodes = Map.new(graph.nodes, &{&1.id, &1})

      Map.new(ids, fn id -> {id, all_nodes[id]} end)
      |> Enum.reject(fn {_id, node} -> is_nil(node) end)
      |> Map.new()
    end
  end

  defp bfs(adjacency, seeds, depth) do
    queue = :queue.from_list(Enum.map(seeds, &{&1, 0}))
    do_bfs(adjacency, queue, MapSet.new(seeds), depth)
  end

  defp do_bfs(_adjacency, queue, seen, _depth) when queue == {[], []}, do: seen

  defp do_bfs(adjacency, queue, seen, depth) do
    case :queue.out(queue) do
      {:empty, _} ->
        seen

      {{:value, {_node, d}}, rest} when d >= depth ->
        do_bfs(adjacency, rest, seen, depth)

      {{:value, {node, d}}, rest} ->
        {next_queue, next_seen} =
          Enum.reduce(Map.get(adjacency, node, []), {rest, seen}, fn target, {q, s} ->
            if MapSet.member?(s, target),
              do: {q, s},
              else: {:queue.in({target, d + 1}, q), MapSet.put(s, target)}
          end)

        do_bfs(adjacency, next_queue, next_seen, depth)
    end
  end

  defp put_node(state, id, types, label, properties) do
    node = Map.get(state.nodes, id, %{id: id, types: [], label: label, properties: %{}})

    node = %{
      node
      | types: (node.types ++ types) |> Enum.uniq() |> Enum.sort(),
        label: node.label || label,
        properties: Map.merge(node.properties || %{}, reject_nil(properties || %{}))
    }

    put_in(state, [:nodes, id], node)
  end

  defp put_edge(state, source, predicate, target, evidence, qualifiers \\ %{}) do
    basis = "#{source}|#{predicate}|#{target}|#{inspect(qualifiers)}"
    id = urn("edge", basis)

    edge = %{
      id: id,
      source: source,
      predicate: predicate,
      target: target,
      evidence: evidence,
      qualifiers: qualifiers
    }

    put_in(state, [:edges, id], edge)
  end

  defp put_fact(state, _subject, _predicate, nil, _evidence), do: state

  defp put_fact(state, subject, predicate, value, evidence),
    do: %{
      state
      | facts: [
          %{subject: subject, predicate: predicate, value: value, evidence: evidence}
          | state.facts
        ]
    }

  defp tables(graph) do
    %{
      nodes:
        Enum.map(graph.nodes, fn node ->
          props = node.properties || %{}

          %{
            id: node.id,
            label: node.label,
            types: node.types,
            repository: props[:repository],
            kind: props[:kind],
            standing: props[:standing],
            cell: props[:cell],
            memory_key: props[:memory_key],
            state: props[:state],
            is_archived: props[:is_archived]
          }
        end),
      edges: graph.edges,
      facts: graph.facts
    }
  end

  defp triples(graph) do
    edge_triples =
      Enum.map(
        graph.edges,
        &%{
          subject: &1.source,
          predicate: "pt:#{String.downcase(&1.predicate)}",
          object: %{id: &1.target},
          evidence: &1.evidence
        }
      )

    fact_triples =
      Enum.map(
        graph.facts,
        &%{
          subject: &1.subject,
          predicate: "pt:#{sanitize(&1.predicate)}",
          object: %{value: &1.value},
          evidence: &1.evidence
        }
      )

    Enum.sort_by(edge_triples ++ fact_triples, &{&1.subject, &1.predicate, inspect(&1.object)})
  end

  defp jsonld(graph) do
    relations =
      Enum.reduce(graph.edges, %{}, fn edge, acc ->
        predicate = "pt:#{String.downcase(edge.predicate)}"

        update_in(
          acc,
          [Access.key(edge.source, %{}), Access.key(predicate, [])],
          &(&1 ++ [%{"@id" => edge.target}])
        )
      end)

    docs =
      Enum.map(graph.nodes, fn node ->
        relation_props = Map.get(relations, node.id, %{})

        Map.merge(
          %{"@id" => node.id, "@type" => ["prov:Entity"], "skos:prefLabel" => node.label},
          relation_props
        )
      end)

    %{
      "@context" => %{
        "@version" => 1.1,
        "pt" => "https://project-two.chatman.dev/vocab/",
        "prov" => "http://www.w3.org/ns/prov#",
        "dcterms" => "http://purl.org/dc/terms/",
        "dcat" => "http://www.w3.org/ns/dcat#",
        "schema" => "https://schema.org/",
        "skos" => "http://www.w3.org/2004/02/skos/core#",
        "foaf" => "http://xmlns.com/foaf/0.1/",
        "doap" => "http://usefulinc.com/ns/doap#"
      },
      "@graph" => docs,
      "profile" => "Project Two explicit-semantics projection",
      "conformance" => "GENERATED_NOT_EXTERNALLY_VALIDATED"
    }
  end

  defp services(graph) do
    memory_nodes = Enum.filter(graph.nodes, &("MemoryRecord" in &1.types))

    facets = fn key ->
      memory_nodes
      |> Enum.map(&Map.get(&1.properties || %{}, key))
      |> Enum.reject(&is_nil/1)
      |> Enum.frequencies()
      |> Enum.into(%{}, fn {k, v} -> {to_string(k), v} end)
    end

    %{
      model: "virtual-semantic-paas",
      canonical_subject: "GitHub Project v2 #2",
      interfaces: [
        %{name: "ChatGPT request bus", protocol: "bounded JSON request + receipt"},
        %{name: "LLM MCP junction", protocol: "AshAi/MCP"},
        %{name: "GitHub Project UI", protocol: "human inspection"}
      ],
      capabilities:
        Enum.map(@capabilities, fn capability ->
          Map.merge(capability, %{
            id: urn("capability", capability.name),
            type: "dcat:DataService",
            authority:
              if(Enum.any?(capability.operations, &mutating_operation?/1),
                do: "BOUNDED_PROJECT_MEMORY_MUTATION",
                else: "READ_ONLY_PROJECTION"
              )
          })
        end),
      resource_facets: %{
        kinds: facets.(:kind),
        repositories: facets.(:repository),
        standings: facets.(:standing),
        cells: facets.(:cell)
      }
    }
  end

  defp ocel(graph) do
    project_items = Enum.filter(graph.nodes, &("ProjectItem" in &1.types))

    objects =
      Enum.map(project_items, fn node ->
        props = node.properties || %{}

        attributes =
          [:title, :repository, :state, :kind, :standing, :cell, :memory_key]
          |> Enum.flat_map(fn name ->
            case props[name] do
              nil -> []
              value -> [%{name: to_string(name), time: graph.observed_at, value: value}]
            end
          end)

        %{
          id: node.id,
          type: if("MemoryRecord" in node.types, do: "MemoryRecord", else: "ProjectItem"),
          attributes: attributes,
          relationships: []
        }
      end)

    snapshot = %{
      id: urn("event", "snapshot:#{graph.observed_at}"),
      type: "ProjectSemanticSnapshot",
      time: graph.observed_at,
      attributes: [],
      relationships: Enum.map(project_items, &%{objectId: &1.id, qualifier: "observed"})
    }

    fact_index = Enum.group_by(graph.facts, & &1.subject)

    memory_events =
      Enum.flat_map(project_items, fn node ->
        by_predicate = Map.new(Map.get(fact_index, node.id, []), &{&1.predicate, &1.value})

        [{"metadata.created_at", "MemoryCreated"}, {"metadata.updated_at", "MemoryUpdated"}]
        |> Enum.flat_map(fn {field, type} ->
          case by_predicate[field] do
            nil ->
              []

            timestamp ->
              [
                %{
                  id: urn("event", "#{type}:#{node.id}:#{timestamp}"),
                  type: type,
                  time: timestamp,
                  attributes: [],
                  relationships: [%{objectId: node.id, qualifier: "subject"}]
                }
              ]
          end
        end)
      end)

    %{
      profile: "OCEL-2-shaped Project Two projection",
      conformance: "NOT_CLAIMED_UNTIL_INDEPENDENT_OCEL_VALIDATOR_EXECUTES",
      objectTypes: [
        %{name: "ProjectItem", attributes: []},
        %{name: "MemoryRecord", attributes: []}
      ],
      eventTypes: [
        %{name: "ProjectSemanticSnapshot", attributes: []},
        %{name: "MemoryCreated", attributes: []},
        %{name: "MemoryUpdated", attributes: []}
      ],
      objects: objects,
      events: [snapshot | memory_events] |> Enum.sort_by(&{to_string(&1.time), &1.id})
    }
  end

  defp stats(graph) do
    %{
      node_count: length(graph.nodes),
      edge_count: length(graph.edges),
      fact_count: length(graph.facts),
      node_types: graph.nodes |> Enum.flat_map(& &1.types) |> Enum.frequencies(),
      edge_predicates: graph.edges |> Enum.map(& &1.predicate) |> Enum.frequencies()
    }
  end

  defp envelope(graph, payload) do
    Map.merge(
      %{
        schema: graph.schema,
        project: graph.project,
        observed_at: graph.observed_at,
        canonical_subject: graph.canonical_subject,
        authority: graph.authority,
        source_truncated: graph.source_truncated
      },
      payload
    )
  end

  defp strip_envelope(result) when is_map(result),
    do:
      Map.drop(result, [
        :schema,
        :project,
        :observed_at,
        :canonical_subject,
        :authority,
        :source_truncated
      ])

  defp reference_target(value, relation_key) when is_binary(value) or is_integer(value) do
    text = to_string(value) |> String.trim()

    cond do
      text == "" ->
        nil

      String.starts_with?(relation_key, "memory") and memory_key?(text) ->
        {urn("memory", text), "MemoryKey"}

      repository?(text) ->
        {urn("repository", text), "Repository"}

      sha?(text) ->
        {urn("commit", String.downcase(text)), "Commit"}

      (String.starts_with?(text, "dfcm/") or String.starts_with?(text, "project/")) and
          memory_key?(text) ->
        {urn("memory", text), "MemoryKey"}

      Map.has_key?(@reference_relations, relation_key) ->
        {urn("reference", text), "Reference"}

      true ->
        nil
    end
  end

  defp reference_target(_, _), do: nil

  defp metadata_predicate(key),
    do:
      "METADATA_" <>
        (key |> String.replace(~r/[^A-Za-z0-9]+/, "_") |> String.trim("_") |> String.upcase())

  defp repository?(text), do: Regex.match?(~r/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/, text)
  defp memory_key?(text), do: Regex.match?(~r/^[A-Za-z0-9_.:-]+(?:\/[A-Za-z0-9_.:@-]+)+$/, text)
  defp sha?(text), do: Regex.match?(~r/^[0-9a-f]{7,64}$/i, text)

  defp mutating_operation?(operation),
    do:
      String.starts_with?(operation, "memory.") and
        operation not in ["memory.read", "memory.query"]

  defp flatten(value, prefix) when is_map(value) do
    value
    |> Enum.sort_by(fn {key, _} -> to_string(key) end)
    |> Enum.flat_map(fn {key, child} -> flatten(child, "#{prefix}.#{key}") end)
  end

  defp flatten(value, prefix) when is_list(value) do
    value
    |> Enum.with_index()
    |> Enum.flat_map(fn {child, index} -> flatten(child, "#{prefix}[#{index}]") end)
  end

  defp flatten(value, prefix), do: [{prefix, value}]

  defp listify(nil), do: []
  defp listify(value) when is_list(value), do: value
  defp listify(value), do: [value]

  defp query_value(query, key, default) when is_map(query),
    do: Map.get(query, key, Map.get(query, String.to_atom(key), default))

  defp query_list(query, key),
    do: query_value(query, key, []) |> listify() |> Enum.map(&to_string/1)

  defp normalize_int(value, _default) when is_integer(value), do: value

  defp normalize_int(value, default) when is_binary(value), do: case(Integer.parse(value)) do
    {int, ""} -> int
    _ -> default
  end

  defp normalize_int(_, default), do: default

  defp stringify_keys(map) when is_map(map), do: Map.new(map, fn {k, v} -> {to_string(k), v} end)
  defp reject_nil(map), do: Map.reject(map, fn {_k, value} -> is_nil(value) end)
  defp sanitize(value), do: value |> to_string() |> String.replace(~r/[^A-Za-z0-9_.-]+/, "_")
  defp urn(kind, value), do: @base <> kind <> ":" <> stable_component(to_string(value))

  defp stable_component(value) do
    if String.length(value) <= 180 and not String.contains?(value, [" ", "\n", "\t", "|"]) do
      value
    else
      :crypto.hash(:sha256, value) |> Base.encode16(case: :lower) |> String.slice(0, 20)
    end
  end

  defp now, do: DateTime.utc_now() |> DateTime.truncate(:second) |> DateTime.to_iso8601()
end
