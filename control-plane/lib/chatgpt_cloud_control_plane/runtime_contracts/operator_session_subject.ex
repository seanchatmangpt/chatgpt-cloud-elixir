defmodule ChatGPTCloudControlPlane.RuntimeContracts.OperatorSessionSubject do
  @moduledoc "Binds operator sessions to authenticated actor identity without granting agent-ingestion authority."

  def validate(%{operator_id: id, session_id: session, channel: :browser})
      when is_binary(id) and id != "" and is_binary(session) and session != "", do: :ok

  def validate(%{channel: :agent}), do: {:error, :operator_session_not_agent_token}
  def validate(_), do: {:error, :invalid_operator_session}
end
