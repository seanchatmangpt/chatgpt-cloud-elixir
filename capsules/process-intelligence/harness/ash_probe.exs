[path] = System.argv()
raw = path |> File.read!() |> Jason.decode!()

events =
  raw["events"]
  |> Enum.map(fn {id, event} ->
    %{
      "ocel:eid" => id,
      "ocel:activity" => event["activity"],
      "ocel:timestamp" => event["timestamp"],
      "ocel:omap" => event["objects"],
      "ocel:vmap" => Map.drop(event, ["activity", "timestamp", "objects"])
    }
  end)
  |> Enum.sort_by(& &1["ocel:timestamp"])

{:ok, metrics} = AshR2RML.Telemetry.OCEL2.validate(events)
{:ok, reconstruction} = AshR2RML.Telemetry.OCEL2.reconstruct_from_events(events)

summary = %{
  engine: "ash_r2rml_ocel2",
  valid: metrics.valid?,
  event_count: metrics.event_count,
  distinct_object_count: metrics.distinct_object_count,
  distinct_activities: Enum.sort(metrics.distinct_activities),
  reconstructed_object_count: map_size(reconstruction.objects),
  activities_order: reconstruction.activities_order
}

IO.puts("PROCESS_LAB_JSON=" <> Jason.encode!(summary))
