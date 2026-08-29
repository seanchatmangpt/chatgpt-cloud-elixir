defmodule ChatGPTCloudControlPlane.RuntimeContracts.ReplayIdentityGuard do
  @moduledoc "Requires replay requests to match the original subject and receipt digest."

  def admit(%{subject_sha: sha, original_subject_sha: sha, receipt_digest: digest}) when is_binary(sha) and sha != "" and is_binary(digest) and digest != "", do: :ok
  def admit(%{subject_sha: current, original_subject_sha: original}), do: {:error, {:replay_subject_mismatch, original, current}}
  def admit(_), do: {:error, :invalid_replay_identity}
end
