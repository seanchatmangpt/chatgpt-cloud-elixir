defmodule ChatGPTCloud.RuntimeIntegration.RuntimeCapabilitySetTest do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.RuntimeIntegration.RuntimeCapabilitySet

  test "complete capability set admits and missing AshAI is explicit" do
    required = RuntimeCapabilitySet.required()
    assert :ok = RuntimeCapabilitySet.admit(required)
    assert {:error, {:missing_runtime_capabilities, [:ash_ai]}} =
             RuntimeCapabilitySet.admit(MapSet.delete(required, :ash_ai))
  end
end
