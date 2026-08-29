defmodule ChatGPTCloudControlPlane.RuntimeContracts.AgentTokenScope do
  @moduledoc "Restricts API tokens to explicit ingestion/query scopes and refuses browser-session substitution."

  @allowed [:ingest_ocel, :read_status, :read_receipt]

  def admit(%{scope: scope, channel: :agent}) when scope in @allowed, do: :ok
  def admit(%{channel: :browser}), do: {:error, :agent_token_not_browser_session}
  def admit(%{scope: scope}), do: {:error, {:unauthorized_agent_scope, scope}}
  def admit(_), do: {:error, :invalid_agent_token_scope}
end
