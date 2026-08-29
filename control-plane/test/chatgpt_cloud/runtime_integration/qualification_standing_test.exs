defmodule ChatGPTCloud.RuntimeIntegration.QualificationStandingTest do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.RuntimeIntegration.QualificationStanding

  test "standing is alive only for successful execution on the exact subject" do
    sha = String.duplicate("7", 40)
    assert :alive = QualificationStanding.derive(sha, %{subject_sha: sha, exit_code: 0, executed: true})
    assert :unknown = QualificationStanding.derive(sha, %{subject_sha: sha, exit_code: 0, executed: false})
    assert :unknown = QualificationStanding.derive(sha, %{subject_sha: String.duplicate("8", 40), exit_code: 0, executed: true})
    assert :build_broken = QualificationStanding.derive(sha, %{subject_sha: sha, exit_code: 1, executed: true})
  end
end
