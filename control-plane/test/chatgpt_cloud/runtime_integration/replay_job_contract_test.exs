defmodule ChatGPTCloud.RuntimeIntegration.ReplayJobContractTest do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.RuntimeIntegration.ReplayJobContract

  test "replay work requires exact subject receipt and replay key" do
    sha = String.duplicate("1", 40)
    assert :ok = ReplayJobContract.admit(%ReplayJobContract{subject_sha: sha, receipt_id: "receipt-1", replay_key: "rk-1"})
    assert {:error, :invalid_replay_job} = ReplayJobContract.admit(%ReplayJobContract{subject_sha: sha, receipt_id: "", replay_key: "rk-1"})
  end
end
