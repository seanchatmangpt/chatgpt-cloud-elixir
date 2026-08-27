defmodule ChatGPTCloudControlPlane.RuntimeContracts.LiveviewSessionGuard do
  @moduledoc "Requires LiveView operator interactions to carry authenticated session identity."

  def admit(%{operator_id: id, session_id: session}) when is_binary(id) and id != "" and is_binary(session) and session != "", do: :ok
  def admit(_), do: {:error, :unauthenticated_liveview_session}
end
