defmodule ChatGPTCloud.EcosystemTest do
  use ExUnit.Case, async: false

  alias ChatGPTCloud.ProcessIntelligence.Qualification

  test "the maximal admitted Ash closure is compiled into real system contracts" do
    receipt = ChatGPTCloud.Ecosystem.verify!()

    assert receipt.standing == "ALIVE"
    assert receipt.missing_modules == []
    assert receipt.state_machine.missing == []
    assert receipt.durable_work.schedules == [:reconcile_pending]

    assert Enum.sort(AshStateMachine.Info.state_machine_all_states(Qualification)) ==
             Enum.sort([:pending, :running, :qualified, :degraded, :blocked, :failed, :retrying])

    assert [%{name: :reconcile_pending}] =
             AshOban.Info.oban_scheduled_actions(Qualification)
  end

  test "machine and AI projections are read-only capability surfaces" do
    assert length(AshJsonApi.Domain.Info.routes(ChatGPTCloud.ProcessIntelligence)) == 4
    assert length(AshGraphql.Domain.Info.queries(ChatGPTCloud.ProcessIntelligence)) == 4

    tools =
      AshAi.exposed_tools(otp_app: :chatgpt_cloud_control_plane)
      |> Enum.filter(&(&1.domain == ChatGPTCloud.ProcessIntelligence))

    names = Enum.map(tools, & &1.name)

    assert :list_qualifications in names
    assert :list_cost_observations in names
    refute Enum.any?(names, &(&1 in [:deploy, :cutover, :actuate, :qualify]))
  end
end
