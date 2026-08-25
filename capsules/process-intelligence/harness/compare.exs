[root, ash_path, ex4pm_path] = System.argv()
ash = ash_path |> File.read!() |> Jason.decode!()
ex4pm = ex4pm_path |> File.read!() |> Jason.decode!()
manifest = root |> Path.join("manifest.json") |> File.read!() |> Jason.decode!()

expected_activities = ["approve", "create", "reject"]
expected_edges = [
  %{"from" => "create", "to" => "approve", "count" => 1},
  %{"from" => "create", "to" => "reject", "count" => 1}
]
expected_paths = [["create", "approve"], ["create", "reject"]]

checks = %{
  "ash_valid" => ash["valid"] == true,
  "event_count_parity" => ash["event_count"] == 4 and ex4pm["event_count"] == 4,
  "object_count_parity" => ash["distinct_object_count"] == 2 and ex4pm["object_count"] == 2,
  "activity_set" => ash["distinct_activities"] == expected_activities,
  "ex4pm_edges" => ex4pm["edges"] == expected_edges,
  "ex4pm_fitness" => ex4pm["fitness"] == 1.0,
  "ex4pm_standing" =>
    Enum.all?(["discovery_standing", "conformance_standing", "simulation_standing"],
      &(ex4pm[&1] == "alive")
    ),
  "simulation_language" =>
    Enum.all?(expected_paths, &(&1 in ex4pm["simulation_paths"]))
}

failed =
  checks
  |> Enum.reject(fn {_name, ok?} -> ok? end)
  |> Enum.map(&elem(&1, 0))
  |> Enum.sort()

canonical = Jason.encode!(%{"ash" => ash, "ex4pm" => ex4pm})
world = File.read!(Path.join(root, "harness/world.json"))
hex = fn binary -> :crypto.hash(:sha256, binary) |> Base.encode16(case: :lower) end

receipt = %{
  "schema_version" => 1,
  "phase" => "process_intelligence_bridge",
  "subjects" => manifest["subjects"],
  "world_sha256" => hex.(world),
  "semantic_observation_sha256" => hex.(canonical),
  "checks" => checks,
  "failed_checks" => failed,
  "standing" => if(failed == [], do: "ALIVE", else: "BUILD_BROKEN"),
  "scope" => "offline_in_memory_process_intelligence",
  "replay" => "bash harness/verify.sh"
}

receipt_path = Path.join(root, "harness/process-lab-receipt.json")
File.write!(receipt_path, Jason.encode_to_iodata!(receipt, pretty: true))
File.write!(receipt_path, "\n", [:append])
IO.puts(Jason.encode!(receipt, pretty: true))

if failed != [], do: System.halt(65)
