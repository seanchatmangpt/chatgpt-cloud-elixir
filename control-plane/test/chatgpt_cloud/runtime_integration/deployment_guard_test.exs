defmodule ChatGPTCloud.RuntimeIntegration.DeploymentGuardTest do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.RuntimeIntegration.DeploymentGuard

  test "missing deployment credential is blocked rather than alive" do
    assert :ok = DeploymentGuard.admit("present")
    assert {:error, {:blocked, :missing_deployment_authority}} = DeploymentGuard.admit(nil)
    assert {:error, {:blocked, :missing_deployment_authority}} = DeploymentGuard.admit("")
  end
end
