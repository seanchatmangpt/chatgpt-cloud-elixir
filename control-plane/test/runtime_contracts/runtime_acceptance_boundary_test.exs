defmodule ChatGPTCloudControlPlane.RuntimeContracts.RuntimeAcceptanceBoundaryTest do
  use ExUnit.Case, async: true
  alias ChatGPTCloudControlPlane.RuntimeContracts.RuntimeAcceptanceBoundary

  test "weaker evidence cannot satisfy stronger acceptance" do
    assert :ok = RuntimeAcceptanceBoundary.admit(:integration, :e2e)
    assert {:error, {:insufficient_acceptance_boundary, :integration, :unit}} = RuntimeAcceptanceBoundary.admit(:integration, :unit)
  end
end
