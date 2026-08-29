defmodule ChatGPTCloud.RuntimeIntegration.RuntimeIntegrationPlanTest do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.RuntimeIntegration.{RuntimeCapabilitySet, RuntimeExtensionWiring, RuntimeIntegrationPlan}

  test "full runtime plan admits and missing GraphQL surface is refused" do
    plan = %RuntimeIntegrationPlan{
      capabilities: RuntimeCapabilitySet.required(),
      extension_wiring: RuntimeExtensionWiring.required(),
      api_surfaces: [:json_api, :graphql],
      queues: [:qualification, :replay, :mining]
    }

    assert :ok = RuntimeIntegrationPlan.admit(plan)
    assert {:error, :runtime_integration_surface_incomplete} = RuntimeIntegrationPlan.admit(%{plan | api_surfaces: [:json_api]})
  end
end
