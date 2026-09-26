defmodule ChatGPTCloudControlPlane.RuntimeContracts.ExactSubjectTest do
  use ExUnit.Case, async: true
  alias ChatGPTCloudControlPlane.RuntimeContracts.ExactSubject
  test "requires repo ref and sha" do
    assert :ok = ExactSubject.validate(%{repo: "r", ref: "main", sha: "abc"})
    assert {:error, {:missing_subject_identity, :sha}} = ExactSubject.validate(%{repo: "r", ref: "main"})
  end
end
