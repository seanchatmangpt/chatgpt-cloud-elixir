defmodule ChatGPTCloudControlPlane.RuntimeContracts.RuntimeReplayContractTest do
  use ExUnit.Case, async: true
  alias ChatGPTCloudControlPlane.RuntimeContracts.RuntimeReplayContract

  test "replay requires subject capsule command and config identity" do
    assert :ok = RuntimeReplayContract.validate(%{subject_sha: "abc", capsule_digest: "cap", command: "mix test", config_digest: "cfg"})
    assert {:error, {:missing_replay_identity, :config_digest}} = RuntimeReplayContract.validate(%{subject_sha: "abc", capsule_digest: "cap", command: "mix test"})
  end
end
