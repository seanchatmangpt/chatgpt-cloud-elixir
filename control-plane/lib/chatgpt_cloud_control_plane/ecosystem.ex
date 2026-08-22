defmodule ChatGPTCloud.Ecosystem do
  @moduledoc """
  Executable registry for the admitted Ash ecosystem closure.

  Presence is not standing. This verifier proves that the selected dependency
  graph loaded and that critical DSL contracts were compiled into the expected
  state-machine and durable-work structures. Runtime service crowns remain
  separately receipted.
  """

  @components [
    {Ash, :domain_and_resource_model},
    {Spark, :dsl_manufacture},
    {Reactor, :saga_orchestration},
    {Igniter, :reproducible_installation},
    {AshPostgres, :persistent_data_layer},
    {AshPhoenix, :phoenix_projection},
    {AshJsonApi, :json_api_projection},
    {AshAuthentication, :human_identity},
    {AshAuthentication.Phoenix, :phoenix_authentication},
    {AshOban, :durable_background_work},
    {AshStateMachine, :lifecycle},
    {AshArchival, :logical_deletion},
    {AshMoney, :cost_observation},
    {AshCloak, :encrypted_attributes},
    {AshGraphql, :graphql_projection},
    {AshAi, :bounded_ai_tools},
    {AshAdmin, :operator_projection},
    {Cloak, :vault_implementation}
  ]

  @required_states [:pending, :running, :qualified, :degraded, :blocked, :failed, :retrying]

  def receipt do
    modules =
      Map.new(@components, fn {module, role} ->
        {inspect(module), %{role: role, loaded: Code.ensure_loaded?(module)}}
      end)

    states =
      if Code.ensure_loaded?(AshStateMachine.Info) do
        AshStateMachine.Info.state_machine_all_states(
          ChatGPTCloud.ProcessIntelligence.Qualification
        )
      else
        []
      end

    schedules =
      if Code.ensure_loaded?(AshOban.Info) do
        AshOban.Info.oban_scheduled_actions(ChatGPTCloud.ProcessIntelligence.Qualification)
        |> Enum.map(& &1.name)
      else
        []
      end

    missing_modules =
      modules
      |> Enum.reject(fn {_name, info} -> info.loaded end)
      |> Enum.map(&elem(&1, 0))
      |> Enum.sort()

    missing_states = @required_states -- states
    missing_schedules = [:reconcile_pending] -- schedules

    %{
      schema_version: 1,
      subject: "chatgpt-cloud-control-plane",
      components: modules,
      state_machine: %{states: states, missing: missing_states},
      durable_work: %{schedules: schedules, missing: missing_schedules},
      missing_modules: missing_modules,
      standing:
        if(missing_modules == [] and missing_states == [] and missing_schedules == [],
          do: "ALIVE",
          else: "BUILD_BROKEN"
        )
    }
  end

  def verify! do
    receipt = receipt()

    if receipt.standing == "ALIVE" do
      receipt
    else
      raise "Ash ecosystem closure failed: #{inspect(receipt)}"
    end
  end
end

defmodule Mix.Tasks.ChatgptCloud.Ecosystem.Verify do
  @shortdoc "Verify the compiled Ash ecosystem closure and emit a JSON receipt"
  use Mix.Task

  @impl Mix.Task
  def run(_args) do
    Mix.Task.run("app.start")
    receipt = ChatGPTCloud.Ecosystem.verify!()
    Mix.shell().info(Jason.encode!(receipt, pretty: true))
  end
end
