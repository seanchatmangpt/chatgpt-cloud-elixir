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

  @runtime_extensions [
    :spark,
    :reactor,
    :igniter,
    :ash_json_api,
    :ash_authentication,
    :ash_oban,
    :ash_state_machine,
    :ash_archival,
    :ash_money,
    :ash_cloak,
    :ash_graphql,
    :ash_ai
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

    runtime_roles =
      Enum.map(@runtime_extensions, fn extension ->
        {:ok, role} = ChatGPTCloud.RuntimeIntegration.ExtensionManifest.role(extension)
        role
      end)

    runtime_contract = ChatGPTCloud.RuntimeIntegration.RuntimeManifest.verify_roles(runtime_roles)

    %{
      schema_version: 2,
      subject: "chatgpt-cloud-control-plane",
      components: modules,
      state_machine: %{states: states, missing: missing_states},
      durable_work: %{schedules: schedules, missing: missing_schedules},
      runtime_integration: %{
        extensions: @runtime_extensions,
        roles: runtime_roles,
        verification: runtime_contract
      },
      missing_modules: missing_modules,
      standing:
        if(
          missing_modules == [] and missing_states == [] and missing_schedules == [] and
            runtime_contract == :ok,
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
