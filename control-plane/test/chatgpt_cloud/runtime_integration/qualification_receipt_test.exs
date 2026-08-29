defmodule ChatGPTCloud.RuntimeIntegration.QualificationReceiptTest do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.RuntimeIntegration.QualificationReceipt

  test "successful receipt is alive only for its exact subject" do
    sha = String.duplicate("d", 40)
    receipt = %QualificationReceipt{subject_sha: sha, command: "mix test", exit_code: 0, standing: :alive}
    assert QualificationReceipt.alive?(receipt, sha)
    refute QualificationReceipt.alive?(receipt, String.duplicate("e", 40))
    refute QualificationReceipt.alive?(%{receipt | exit_code: 1}, sha)
  end
end
