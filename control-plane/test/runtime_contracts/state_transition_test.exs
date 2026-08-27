defmodule ChatGPTCloudControlPlane.RuntimeContracts.StateTransitionTest do
  use ExUnit.Case, async: true
  alias ChatGPTCloudControlPlane.RuntimeContracts.StateTransition
  test "admits only declared nonterminal edges" do
    assert :ok = StateTransition.validate(:queued, :running, [{:queued, :running}])
    assert {:error, :terminal_state_transition} = StateTransition.validate(:completed, :running, [{:completed, :running}])
  end
end
