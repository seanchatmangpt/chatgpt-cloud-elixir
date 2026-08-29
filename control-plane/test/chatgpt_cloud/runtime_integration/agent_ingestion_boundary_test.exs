defmodule ChatGPTCloud.RuntimeIntegration.AgentIngestionBoundaryTest do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.RuntimeIntegration.AgentIngestionBoundary

  test "agent ingestion accepts only verified ingestion scopes" do
    assert :ok = AgentIngestionBoundary.admit(%{agent_id: "a-1", token_verified: true, scope: :ingest_ocel})
    assert {:error, :agent_scope_refused} = AgentIngestionBoundary.admit(%{agent_id: "a-1", token_verified: true, scope: :deploy})
    assert {:error, :invalid_agent_token} = AgentIngestionBoundary.admit(%{agent_id: "a-1", token_verified: false, scope: :ingest_ocel})
  end
end
