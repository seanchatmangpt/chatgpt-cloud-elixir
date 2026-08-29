defmodule ChatGPTCloud.RuntimeIntegration.ExactSubjectTest do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.RuntimeIntegration.ExactSubject

  test "admits forty-character source identity and refuses abbreviated SHA" do
    sha = String.duplicate("a", 40)
    assert {:ok, %ExactSubject{repository: "owner/repo", ref: "main", sha: ^sha}} = ExactSubject.new("owner/repo", "main", sha)
    assert {:error, :invalid_sha} = ExactSubject.new("owner/repo", "main", "abc")
  end
end
