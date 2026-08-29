defmodule ChatGPTCloud.RuntimeIntegration.MiningJobContractTest do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.RuntimeIntegration.MiningJobContract

  test "mining job references wasm4pm and refuses local algorithm ownership" do
    sha = String.duplicate("2", 40)
    assert :ok = MiningJobContract.admit(%MiningJobContract{subject_sha: sha, algorithm_ref: "ocel:discover", owner: "wasm4pm"})
    assert {:error, :process_intelligence_ownership_escape} = MiningJobContract.admit(%MiningJobContract{subject_sha: sha, algorithm_ref: "ocel:discover", owner: "control-plane"})
  end
end
