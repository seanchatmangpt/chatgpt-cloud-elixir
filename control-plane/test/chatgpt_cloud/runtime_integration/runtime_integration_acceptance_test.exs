defmodule ChatGPTCloud.RuntimeIntegration.RuntimeIntegrationAcceptanceTest do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.RuntimeIntegration.{RuntimeCapabilitySet, RuntimeExtensionWiring, RuntimeIntegrationAcceptance, RuntimeIntegrationPlan}

  test "integrated plan is ALIVE only for successful exact-subject execution" do
    sha = String.duplicate("9", 40)

    plan = %RuntimeIntegrationPlan{
      capabilities: RuntimeCapabilitySet.required(),
      extension_wiring: RuntimeExtensionWiring.required(),
      api_surfaces: [:json_api, :graphql],
      queues: [:qualification, :replay, :mining]
    }

    assert :alive = RuntimeIntegrationAcceptance.evaluate(plan, sha, %{subject_sha: sha, exit_code: 0, executed: true})
    assert :unknown = RuntimeIntegrationAcceptance.evaluate(plan, sha, %{subject_sha: sha, exit_code: 0, executed: false})
  end
end
