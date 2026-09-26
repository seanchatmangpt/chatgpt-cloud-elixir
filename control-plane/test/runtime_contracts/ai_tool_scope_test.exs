defmodule ChatGPTCloudControlPlane.RuntimeContracts.AiToolScopeTest do
  use ExUnit.Case, async: true
  alias ChatGPTCloudControlPlane.RuntimeContracts.AiToolScope
  test "permits read/query and refuses actuation" do
    assert :ok = AiToolScope.validate(:query)
    assert {:error, :ai_actuation_refused} = AiToolScope.validate(:deploy)
  end
end
