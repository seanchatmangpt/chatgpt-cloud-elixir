defmodule ChatGPTCloudControlPlane.RuntimeContracts.DockerImageReceipt do
  @moduledoc "Binds container image qualification to exact source and immutable image digest."

  def validate(%{subject_sha: sha, image_digest: "sha256:" <> digest, exit: 0})
      when is_binary(sha) and sha != "" and byte_size(digest) >= 32, do: :ok

  def validate(_), do: {:error, :invalid_image_receipt}
end
