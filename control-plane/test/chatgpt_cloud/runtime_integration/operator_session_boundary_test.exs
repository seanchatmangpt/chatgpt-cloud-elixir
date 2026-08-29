defmodule ChatGPTCloud.RuntimeIntegration.OperatorSessionBoundaryTest do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.RuntimeIntegration.OperatorSessionBoundary

  test "admits scoped operator sessions and refuses missing identity" do
    assert {:ok, session} = OperatorSessionBoundary.admit(%{operator_id: "op-1", session_id: "session-1", scopes: [:read]})
    assert OperatorSessionBoundary.permits?(session, :read)
    refute OperatorSessionBoundary.permits?(session, :deploy)
    assert {:error, :operator_session_required} = OperatorSessionBoundary.admit(%{operator_id: "op-1"})
  end
end
