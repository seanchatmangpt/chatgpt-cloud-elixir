defmodule ChatGPTCloudControlPlane.RuntimeContracts.WasmRuntimeIdentityTest do
  use ExUnit.Case, async: true
  alias ChatGPTCloudControlPlane.RuntimeContracts.WasmRuntimeIdentity

  test "requires module export ABI fuel and memory identity" do
    assert :ok = WasmRuntimeIdentity.validate(%{module_digest: "abc", export: "run", abi: "wasm32", fuel: 1000, memory_bytes: 65_536})
    assert {:error, :invalid_wasm_runtime_identity} = WasmRuntimeIdentity.validate(%{module_digest: "abc", export: "run", abi: "wasm32", fuel: 0, memory_bytes: 65_536})
  end
end
