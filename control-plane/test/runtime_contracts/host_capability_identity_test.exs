defmodule ChatGPTCloudControlPlane.RuntimeContracts.HostCapabilityIdentityTest do
  use ExUnit.Case, async: true
  alias ChatGPTCloudControlPlane.RuntimeContracts.HostCapabilityIdentity

  test "consequential runtime requires explicit host capabilities" do
    assert :ok = HostCapabilityIdentity.validate(%{host: "consumer", capability_digest: "abc", capabilities: [:beam]})
    assert {:error, :invalid_host_capability_identity} = HostCapabilityIdentity.validate(%{host: "consumer", capabilities: []})
  end
end
