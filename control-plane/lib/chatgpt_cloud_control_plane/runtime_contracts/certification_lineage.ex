defmodule ChatGPTCloudControlPlane.RuntimeContracts.CertificationLineage do
  @moduledoc "Binds certified standing to an exact subject and certification digest."

  def validate(%{subject_sha: sha, certification_digest: digest, standing: standing})
      when is_binary(sha) and sha != "" and is_binary(digest) and digest != "" and
             standing in [:ALIVE, :PARTIAL_ALIVE], do: :ok

  def validate(_), do: {:error, :invalid_certification_lineage}
end
