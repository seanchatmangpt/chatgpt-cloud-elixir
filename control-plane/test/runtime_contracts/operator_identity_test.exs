defmodule ChatGPTCloudControlPlane.RuntimeContracts.OperatorIdentityTest do
  use ExUnit.Case, async: true
  alias ChatGPTCloudControlPlane.RuntimeContracts.OperatorIdentity
  test "requires actor and session" do
    assert :ok = OperatorIdentity.validate(%{actor_id: "u1", session_id: "s1"})
    assert {:error, :operator_identity_missing} = OperatorIdentity.validate(%{actor_id: "u1"})
  end
end
