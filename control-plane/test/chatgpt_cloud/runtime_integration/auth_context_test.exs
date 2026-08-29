defmodule ChatGPTCloud.RuntimeIntegration.AuthContextTest do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.RuntimeIntegration.AuthContext

  test "constructs typed operator and agent identities with explicit scopes" do
    operator = AuthContext.new(:operator, "op-1", [:read, :admin])
    agent = AuthContext.new(:agent, "agent-1", [:ingest])
    assert operator.kind == :operator
    assert operator.scopes == [:read, :admin]
    assert agent.kind == :agent
    assert agent.scopes == [:ingest]
  end
end
