defmodule ChatGPTCloudControlPlane.RuntimeContracts.StateTransitionGuardTest do
  use ExUnit.Case, async: true
  alias ChatGPTCloudControlPlane.RuntimeContracts.StateTransitionGuard

  test "admits explicit progress and refuses implicit terminal jumps" do
    assert :ok = StateTransitionGuard.admit(:pending, :running)
    assert {:error, {:invalid_transition, :pending, :succeeded}} = StateTransitionGuard.admit(:pending, :succeeded)
  end
end
