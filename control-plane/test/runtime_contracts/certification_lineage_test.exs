defmodule ChatGPTCloudControlPlane.RuntimeContracts.CertificationLineageTest do
  use ExUnit.Case, async: true
  alias ChatGPTCloudControlPlane.RuntimeContracts.CertificationLineage

  test "certified standing requires exact subject and certification digest" do
    assert :ok = CertificationLineage.validate(%{subject_sha: "abc", certification_digest: "cert", standing: :ALIVE})
    assert {:error, :invalid_certification_lineage} = CertificationLineage.validate(%{subject_sha: "abc", standing: :ALIVE})
  end
end
