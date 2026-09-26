defmodule ChatGPTCloudControlPlane.RuntimeContracts.BuildIdentity do
  @moduledoc "Binds runtime build identity to exact subject, toolchain, and artifact digest."

  def validate(%{subject_sha: sha, toolchain: toolchain, artifact_digest: digest})
      when is_binary(sha) and sha != "" and is_binary(toolchain) and toolchain != "" and is_binary(digest) and digest != "", do: :ok

  def validate(_), do: {:error, :invalid_build_identity}
end
