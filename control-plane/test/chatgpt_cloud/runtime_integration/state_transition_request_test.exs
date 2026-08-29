defmodule ChatGPTCloud.RuntimeIntegration.StateTransitionRequestTest do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.RuntimeIntegration.StateTransitionRequest

  test "terminal transitions require explicit changed state and reason" do
    transition = %StateTransitionRequest{run_id: "run-1", from: :qualifying, to: :alive, reason: "exact-head crown passed"}
    assert :ok = StateTransitionRequest.admit(transition)
    assert StateTransitionRequest.terminal?(transition)
    assert {:error, :invalid_state_transition} = StateTransitionRequest.admit(%{transition | to: :qualifying})
  end
end
