defmodule ChatGPTCloudControlPlane.RuntimeContracts.ProcessIntelligenceFenceTest do
  use ExUnit.Case, async: true
  alias ChatGPTCloudControlPlane.RuntimeContracts.ProcessIntelligenceFence
  test "permits only wasm4pm owners" do
    assert :ok = ProcessIntelligenceFence.validate("wasm4pm")
    assert {:error, {:process_intelligence_owner_refused, "chatgpt-cloud-elixir"}} = ProcessIntelligenceFence.validate("chatgpt-cloud-elixir")
  end
end
