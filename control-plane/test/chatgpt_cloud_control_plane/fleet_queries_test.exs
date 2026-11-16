defmodule ChatGPTCloud.ProcessIntelligence.FleetQueriesTest do
  use ExUnit.Case, async: false

  alias ChatGPTCloud.ProcessIntelligence.Queries
  alias ChatGPTCloud.Repo

  setup do
    pid = Ecto.Adapters.SQL.Sandbox.start_owner!(Repo, shared: true)
    on_exit(fn -> Ecto.Adapters.SQL.Sandbox.stop_owner(pid) end)
    :ok
  end

  defp insert_event(attrs) do
    now = DateTime.utc_now() |> DateTime.truncate(:microsecond)

    defaults = %{
      event_key: "evt-" <> Ecto.UUID.generate(),
      agent_key: "agent-1",
      run_key: "run-1",
      activity: "AgentSpawn",
      lifecycle: "start",
      sequence: System.unique_integer([:positive]),
      standing: "PASS",
      authority_domain: "test",
      occurred_at: now,
      ingested_at: now,
      digest: "d" <> Ecto.UUID.generate(),
      payload: %{}
    }

    row = Enum.reduce(attrs, defaults, fn {k, v}, acc -> Map.put(acc, k, v) end)

    Repo.query!(
      """
      INSERT INTO ocel_events
        (id, event_key, agent_key, run_key, activity, lifecycle, sequence, standing,
         authority_domain, occurred_at, ingested_at, digest, payload, inserted_at, updated_at)
      VALUES ($1::uuid,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15)
      """,
      [
        Ecto.UUID.dump!(Ecto.UUID.generate()),
        row.event_key,
        row.agent_key,
        row.run_key,
        row.activity,
        row.lifecycle,
        row.sequence,
        row.standing,
        row.authority_domain,
        row.occurred_at,
        row.ingested_at,
        row.digest,
        row.payload,
        now,
        now
      ]
    )
  end

  test "lanes_active counts distinct agent keys inside the window" do
    insert_event(agent_key: "a")
    insert_event(agent_key: "b", activity: "AgentComplete", standing: "PASS")
    insert_event(agent_key: "a", occurred_at: DateTime.add(DateTime.utc_now(), -3_600))

    assert Queries.lanes_active(window_seconds: 300) == 2
    assert Queries.lanes_active(window_seconds: 60) == 2
  end

  test "lane_latency percentiles over AgentSpawn/AgentComplete pairs" do
    insert_event(
      activity: "AgentSpawn",
      occurred_at: DateTime.add(DateTime.utc_now(), -100)
    )

    insert_event(
      activity: "AgentComplete",
      standing: "PASS",
      occurred_at: DateTime.add(DateTime.utc_now(), -50)
    )

    latency = Queries.lane_latency(window_seconds: 300)
    assert latency.samples == 1
    assert_in_delta latency.p50_seconds, 50.0, 1.0
    assert_in_delta latency.p95_seconds, 50.0, 1.0
  end

  test "completions_by_standing groups AgentComplete events only" do
    insert_event(activity: "AgentComplete", standing: "PASS")
    insert_event(activity: "AgentComplete", standing: "PASS")
    insert_event(activity: "AgentComplete", standing: "FAIL", run_key: "run-2")
    insert_event(activity: "AgentSpawn", standing: "PASS", run_key: "run-3")

    assert Queries.completions_by_standing(window_seconds: 300) == %{"FAIL" => 1, "PASS" => 2}
  end

  test "events_per_minute buckets and fleet_snapshot aggregates" do
    insert_event(activity: "AgentSpawn")

    rows = Queries.events_per_minute(window_seconds: 300)
    assert [%{events: 1} | _] = rows
    assert Enum.all?(rows, &is_binary(&1.minute))

    snapshot = Queries.fleet_snapshot(window_seconds: 300)
    assert snapshot.lanes_active == 1
    assert snapshot.lane_latency.samples == 0
    assert snapshot.completions_by_standing == %{}
    assert %{
             window_seconds: 300,
             lanes_active: _,
             lane_latency: _,
             completions_by_standing: _,
             events_per_minute: _
           } = snapshot
  end
end
