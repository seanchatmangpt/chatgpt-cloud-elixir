defmodule ChatGPTCloudControlPlane.RuntimeContracts.ReplayIdentityTest do
  use ExUnit.Case, async: true
  alias ChatGPTCloudControlPlane.RuntimeContracts.ReplayIdentity
  test "binds subject command config and toolchain" do
    digest = String.duplicate("a", 32)
    assert :ok = ReplayIdentity.validate(%{subject_digest: digest, command_digest: digest, config_digest: digest, toolchain_digest: digest})
    assert {:error, :replay_identity_incomplete} = ReplayIdentity.validate(%{subject_digest: digest})
  end
end
