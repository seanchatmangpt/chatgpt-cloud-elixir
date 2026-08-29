defmodule ChatGPTCloudControlPlane.RuntimeContracts.AiToolAuthorityGuardTest do
  use ExUnit.Case, async: true
  alias ChatGPTCloudControlPlane.RuntimeContracts.AiToolAuthorityGuard

  test "AI tools may query but cannot deploy" do
    assert :ok = AiToolAuthorityGuard.admit(%{operation: :query})
    assert {:error, {:ai_tool_do_refused, :deploy}} = AiToolAuthorityGuard.admit(%{operation: :deploy})
  end
end
