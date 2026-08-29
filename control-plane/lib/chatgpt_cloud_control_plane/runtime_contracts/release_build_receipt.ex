defmodule ChatGPTCloudControlPlane.RuntimeContracts.ReleaseBuildReceipt do
  @moduledoc "Requires release-build evidence to bind the exact source SHA and successful command exit."

  def validate(%{subject_sha: sha, artifact_digest: digest, exit: 0})
      when is_binary(sha) and sha != "" and is_binary(digest) and digest != "", do: :ok

  def validate(%{exit: exit}) when is_integer(exit), do: {:error, {:release_build_failed, exit}}
  def validate(_), do: {:error, :invalid_release_build_receipt}
end
