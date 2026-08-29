defmodule ChatGPTCloud.RuntimeIntegration.ReplayAdmissionTest do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.RuntimeIntegration.ReplayAdmission

  test "replay requires successful exact-subject source receipt" do
    sha = String.duplicate("5", 40)
    assert :ok = ReplayAdmission.admit(sha, %{subject_sha: sha, exit_code: 0})
    assert {:error, :source_execution_failed} = ReplayAdmission.admit(sha, %{subject_sha: sha, exit_code: 1})
    assert {:error, :receipt_subject_mismatch} = ReplayAdmission.admit(sha, %{subject_sha: String.duplicate("6", 40), exit_code: 0})
  end
end
