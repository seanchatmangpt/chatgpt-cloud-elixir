defmodule ChatGPTCloud.RuntimeIntegration.QualificationJobContractTest do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.RuntimeIntegration.QualificationJobContract

  test "admits exact jobs and refuses exhausted retry budgets" do
    sha = String.duplicate("f", 40)
    assert :ok = QualificationJobContract.admit(%QualificationJobContract{subject_sha: sha, command: "mix test", attempt: 1, max_attempts: 3})
    assert {:error, :retry_budget_exhausted} = QualificationJobContract.admit(%QualificationJobContract{subject_sha: sha, command: "mix test", attempt: 4, max_attempts: 3})
  end
end
