defmodule ChatGPTCloudControlPlane.RuntimeContracts.CapsuleExecutionIdentity do
  @moduledoc "Binds runtime execution to the exact capsule identity and digest used by the consumer."

  def validate(%{capsule: capsule, digest: digest, subject_sha: sha})
      when is_binary(capsule) and capsule != "" and is_binary(digest) and digest != "" and is_binary(sha) and sha != "", do: :ok

  def validate(_), do: {:error, :invalid_capsule_execution_identity}
end
