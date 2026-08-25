[path] = System.argv()
raw = path |> File.read!() |> Jason.decode!()

{:ok, dataset} = Ex4pm.ingest(raw)
{:ok, discovery} = Ex4pm.discover(dataset, algorithm: :dfg, object_type: "Order")
{:ok, conformance} = Ex4pm.conform(dataset, discovery.value, object_type: "Order")
{:ok, simulation} = Ex4pm.simulate(discovery.value, max_depth: 5, max_paths: 32)

edges =
  discovery.value.edges
  |> Enum.map(fn {{from, to}, stats} ->
    %{"from" => from, "to" => to, "count" => stats.count}
  end)
  |> Enum.sort_by(&{&1["from"], &1["to"]})

summary = %{
  engine: "ex4pm_beam",
  event_count: length(dataset.events),
  object_count: map_size(dataset.objects),
  discovery_standing: to_string(discovery.standing),
  conformance_standing: to_string(conformance.standing),
  simulation_standing: to_string(simulation.standing),
  fitness: conformance.value.fitness,
  edges: edges,
  simulation_paths: Enum.sort(simulation.value.paths),
  discovery_receipt_hash: discovery.receipt.hash,
  conformance_receipt_hash: conformance.receipt.hash,
  simulation_receipt_hash: simulation.receipt.hash
}

IO.puts("PROCESS_LAB_JSON=" <> Jason.encode!(summary))
