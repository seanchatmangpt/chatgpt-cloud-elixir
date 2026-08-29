defmodule ChatGPTCloud.RuntimeIntegration.RuntimeIntegrationPlan do
  @moduledoc """Composes the admitted runtime capabilities, extension wiring, API surfaces, queues and authority fences."""

  alias ChatGPTCloud.RuntimeIntegration.{RuntimeCapabilitySet, RuntimeExtensionWiring}

  @enforce_keys [:capabilities, :extension_wiring, :api_surfaces, :queues]
  defstruct [:capabilities, :extension_wiring, :api_surfaces, :queues]

  @type t :: %__MODULE__{
          capabilities: Enumerable.t(),
          extension_wiring: map(),
          api_surfaces: [atom()],
          queues: [atom()]
        }

  @spec admit(t()) :: :ok | {:error, term()}
  def admit(%__MODULE__{} = plan) do
    with :ok <- RuntimeCapabilitySet.admit(plan.capabilities),
         :ok <- RuntimeExtensionWiring.verify(plan.extension_wiring),
         true <- Enum.sort(plan.api_surfaces) == [:graphql, :json_api],
         true <- MapSet.new(plan.queues) == MapSet.new([:qualification, :replay, :mining]) do
      :ok
    else
      false -> {:error, :runtime_integration_surface_incomplete}
      {:error, _} = error -> error
    end
  end
end
