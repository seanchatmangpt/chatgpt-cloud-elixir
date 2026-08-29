defmodule ChatGPTCloud.ProcessIntelligence.SwarmTest do
  @moduledoc """
  Chicago-style state-based tests against the real Postgres-backed swarm
  resources -- no mocks. The concurrent-claim test is the concrete falsifier
  for the "unique-constraint replaces file-lock" invariant from the
  swarmsh -> Ash conversion plan: it exercises two real concurrent
  processes against a real Ash action and asserts on the real persisted
  outcome (exactly one claim wins), not on which function was called.
  """

  use ChatGPTCloud.DataCase, async: false

  alias ChatGPTCloud.ProcessIntelligence.{SwarmAgent, SwarmTeam, SwarmWorkItem}

  test "registers a swarm agent and transitions through its lifecycle" do
    agent =
      SwarmAgent
      |> Ash.Changeset.for_create(:register, %{
        agent_key: "agent_test_#{System.unique_integer([:positive])}",
        team_key: "team_alpha",
        role: "worker",
        specialization: "general_development",
        capacity: 0.8
      })
      |> Ash.create!()

    assert agent.state == :idle
    assert agent.last_heartbeat_at != nil

    agent = agent |> Ash.Changeset.for_update(:start_work, %{}) |> Ash.update!()
    assert agent.state == :working

    agent = agent |> Ash.Changeset.for_update(:go_idle, %{}) |> Ash.update!()
    assert agent.state == :idle
    assert agent.current_work_key == nil
  end

  test "a work item moves pending -> active -> completed" do
    work =
      SwarmWorkItem
      |> Ash.Changeset.for_create(:create, %{
        work_item_id: "work_test_#{System.unique_integer([:positive])}",
        work_type: "feature",
        priority: 90,
        team_key: "team_alpha"
      })
      |> Ash.create!()

    assert work.state == :pending
    assert work.version == 0

    work =
      work
      |> Ash.Changeset.for_update(:claim, %{claimed_by_agent_key: "agent_1"})
      |> Ash.update!()

    assert work.state == :active
    assert work.claimed_by_agent_key == "agent_1"
    assert work.claimed_at != nil
    assert work.version == 1
    assert work.attempt_count == 1

    work = work |> Ash.Changeset.for_update(:complete, %{}) |> Ash.update!()
    assert work.state == :completed
  end

  test "exactly one of two concurrent claimants wins the same work item" do
    work =
      SwarmWorkItem
      |> Ash.Changeset.for_create(:create, %{
        work_item_id: "work_race_#{System.unique_integer([:positive])}",
        work_type: "bugfix",
        priority: 50,
        team_key: "team_alpha"
      })
      |> Ash.create!()

    parent = self()

    claim_attempt = fn agent_key ->
      Task.async(fn ->
        Ecto.Adapters.SQL.Sandbox.allow(ChatGPTCloud.Repo, parent, self())

        result =
          work
          |> Ash.Changeset.for_update(:claim, %{claimed_by_agent_key: agent_key})
          |> Ash.update()

        result
      end)
    end

    [t1, t2] = [claim_attempt.("agent_racer_1"), claim_attempt.("agent_racer_2")]
    results = [Task.await(t1, 5000), Task.await(t2, 5000)]

    successes = Enum.filter(results, &match?({:ok, _}, &1))
    failures = Enum.filter(results, &match?({:error, _}, &1))

    assert length(successes) == 1,
           "expected exactly one winning claim, got #{length(successes)} of 2"

    assert length(failures) == 1

    {:ok, winner} = hd(successes)
    assert winner.state == :active
    assert winner.claimed_by_agent_key in ["agent_racer_1", "agent_racer_2"]

    persisted = Ash.get!(SwarmWorkItem, work.id)
    assert persisted.claimed_by_agent_key == winner.claimed_by_agent_key
    assert persisted.state == :active
  end

  test "team velocity aggregates completed work item priority" do
    team_key = "team_velocity_#{System.unique_integer([:positive])}"

    team =
      SwarmTeam
      |> Ash.Changeset.for_create(:create, %{team_key: team_key, name: "Velocity Team"})
      |> Ash.create!()

    for {work_id_suffix, priority, complete?} <- [{"a", 10, true}, {"b", 20, true}, {"c", 5, false}] do
      work =
        SwarmWorkItem
        |> Ash.Changeset.for_create(:create, %{
          work_item_id: "work_vel_#{team_key}_#{work_id_suffix}",
          priority: priority,
          team_key: team_key
        })
        |> Ash.create!()

      if complete? do
        work
        |> Ash.Changeset.for_update(:claim, %{claimed_by_agent_key: "agent_v"})
        |> Ash.update!()
        |> Ash.Changeset.for_update(:complete, %{})
        |> Ash.update!()
      end
    end

    reloaded = Ash.get!(SwarmTeam, team.id, load: [:velocity, :completed_work_item_count])
    assert reloaded.completed_work_item_count == 2
    assert reloaded.velocity == 30
  end
end
