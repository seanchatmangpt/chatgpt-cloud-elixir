defmodule ChatGPTCloudControlPlane.RuntimeContracts.LifecycleCompletionGuardTest do
  use ExUnit.Case, async: true
  alias ChatGPTCloudControlPlane.RuntimeContracts.StateMachineTerminal

  test "completed lifecycle requires an observed admitted transition" do
    assert :ok = StateMachineTerminal.validate(:completed, %{transition_observed: true, transition_admitted: true})
    assert {:error, :implicit_terminal_state_refused} = StateMachineTerminal.validate(:completed, %{transition_observed: false, transition_admitted: true})
  end
end
