defmodule ChatGPTCloud.RuntimeIntegration.ReplayContractTest do
  use ExUnit.Case, async: true
  alias ChatGPTCloud.RuntimeIntegration.ReplayContract

  test "replay refuses contracts missing verifier identity" do
    contract = %{subject_sha: String.duplicate("a", 40), toolchain: "otp29", command: "mix test"}
    assert {:error, {:missing_replay_field, :verifier_sha}} = ReplayContract.validate(contract)
  end

  test "complete exact replay identity is admitted" do
    contract = %{
      subject_sha: String.duplicate("a", 40),
      verifier_sha: String.duplicate("b", 40),
      toolchain: "otp29",
      command: "mix test"
    }

    assert :ok = ReplayContract.validate(contract)
  end
end
