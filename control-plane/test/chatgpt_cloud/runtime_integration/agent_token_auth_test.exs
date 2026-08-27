defmodule ChatGPTCloud.RuntimeIntegration.AgentTokenAuthTest do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.RuntimeIntegration.AgentTokenAuth

  test "accepts exact token and refuses mismatches or missing identity" do
    assert :ok = AgentTokenAuth.verify("alpha", "alpha")
    assert {:error, :invalid_agent_token} = AgentTokenAuth.verify("alpha", "bravo")
    assert {:error, :invalid_agent_token} = AgentTokenAuth.verify(nil, "alpha")
  end
end
