defmodule ChatGPTCloud.RuntimeIntegration.InteropBoundaryTest do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.RuntimeIntegration.InteropBoundary

  test "admits only wasm4pm process-intelligence ownership" do
    assert :ok = InteropBoundary.validate(%{process_intelligence_owner: "wasm4pm"})
    assert :ok = InteropBoundary.validate(%{process_intelligence_owner: "wasm4pm-compat"})
    assert {:error, :process_intelligence_ownership_escape} = InteropBoundary.validate(%{process_intelligence_owner: "control-plane"})
  end
end
