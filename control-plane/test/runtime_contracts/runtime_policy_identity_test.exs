defmodule ChatGPTCloudControlPlane.RuntimeContracts.RuntimePolicyIdentityTest do
  use ExUnit.Case, async: true
  alias ChatGPTCloudControlPlane.RuntimeContracts.RuntimePolicyIdentity

  test "requires policy id digest and authority scope" do
    assert :ok = RuntimePolicyIdentity.validate(%{policy_id: "runtime", policy_digest: "abc", authority_scope: "read"})
    assert {:error, :invalid_runtime_policy_identity} = RuntimePolicyIdentity.validate(%{policy_id: "runtime"})
  end
end
