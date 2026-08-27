defmodule ChatGPTCloudControlPlane.RuntimeContracts.RuntimePolicyIdentity do
  @moduledoc "Maps Ash/Reactor execution policy to the governed runtime adapter policy identity contract."

  def validate(%{policy_id: id, policy_digest: digest, authority_scope: scope})
      when is_binary(id) and id != "" and is_binary(digest) and digest != "" and is_binary(scope) and scope != "", do: :ok

  def validate(_), do: {:error, :invalid_runtime_policy_identity}
end
