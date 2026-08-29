defmodule ChatGPTCloud.RuntimeIntegration.RuntimeCapabilitySet do
  @moduledoc """Capability closure required by the Project #2 Ash-native control-plane objective."""

  @required MapSet.new([
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
            ])

  @spec required() :: MapSet.t(atom())
  def required, do: @required

  @spec admit(Enumerable.t()) :: :ok | {:error, {:missing_runtime_capabilities, [atom()]}}
  def admit(capabilities) do
    actual = MapSet.new(capabilities)
    missing = @required |> MapSet.difference(actual) |> Enum.sort()
    if missing == [], do: :ok, else: {:error, {:missing_runtime_capabilities, missing}}
  end
end
