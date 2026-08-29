defmodule ChatGPTCloud.RuntimeIntegration.AgentIngestionBoundary do
  @moduledoc """Separates authenticated agent ingestion from operator and deployment authority."""

  @allowed_scopes [:ingest_ocel, :append_receipt]

  @spec admit(map()) :: :ok | {:error, atom()}
  def admit(%{agent_id: agent_id, token_verified: true, scope: scope})
      when is_binary(agent_id) and agent_id != "" and scope in @allowed_scopes,
      do: :ok

  def admit(%{token_verified: false}), do: {:error, :invalid_agent_token}
  def admit(%{scope: _}), do: {:error, :agent_scope_refused}
  def admit(_), do: {:error, :agent_identity_required}
end
