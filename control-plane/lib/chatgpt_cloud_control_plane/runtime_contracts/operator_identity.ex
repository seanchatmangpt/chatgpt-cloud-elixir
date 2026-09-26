defmodule ChatGPTCloudControlPlane.RuntimeContracts.OperatorIdentity do
  @moduledoc "Requires authenticated operator/session identity for human control-plane actions."

  def validate(%{actor_id: id, session_id: session}) when is_binary(id) and id != "" and is_binary(session) and session != "", do: :ok
  def validate(_), do: {:error, :operator_identity_missing}
end
