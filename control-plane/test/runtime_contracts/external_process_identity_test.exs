defmodule ChatGPTCloudControlPlane.RuntimeContracts.ExternalProcessIdentityTest do
  use ExUnit.Case, async: true
  alias ChatGPTCloudControlPlane.RuntimeContracts.ExternalProcessIdentity

  test "requires executable digest and registry identity" do
    assert :ok = ExternalProcessIdentity.validate(%{executable: "pm4py", executable_digest: "abc", registry_id: "runtime-registry"})
    assert {:error, :invalid_external_process_identity} = ExternalProcessIdentity.validate(%{executable: "pm4py", executable_digest: "abc"})
  end
end
