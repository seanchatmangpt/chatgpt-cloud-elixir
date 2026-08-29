defmodule ChatGPTCloudControlPlane.RuntimeContracts.TokenRotationGuard do
  @moduledoc "Requires agent token rotation to preserve actor identity while replacing secret material."

  def admit(%{agent_id: id, old_fingerprint: old, new_fingerprint: new})
      when is_binary(id) and id != "" and is_binary(old) and old != "" and is_binary(new) and new != "" and old != new, do: :ok

  def admit(_), do: {:error, :invalid_token_rotation}
end
