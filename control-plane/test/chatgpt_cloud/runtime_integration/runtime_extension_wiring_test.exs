defmodule ChatGPTCloud.RuntimeIntegration.RuntimeExtensionWiringTest do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.RuntimeIntegration.RuntimeExtensionWiring

  test "complete wiring admits and missing Reactor responsibility is explicit" do
    required = RuntimeExtensionWiring.required()
    assert :ok = RuntimeExtensionWiring.verify(required)
    assert {:error, {:missing_extension_wiring, [:reactor]}} =
             RuntimeExtensionWiring.verify(Map.delete(required, :reactor))
  end
end
