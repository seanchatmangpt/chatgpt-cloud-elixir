defmodule ChatGPTCloudControlPlane.RuntimeContracts.WasmRuntimeIdentity do
  @moduledoc "Binds WASM adapter execution to module digest, export, ABI, fuel, and memory limits."

  def validate(%{module_digest: digest, export: export, abi: abi, fuel: fuel, memory_bytes: memory})
      when is_binary(digest) and digest != "" and is_binary(export) and export != "" and is_binary(abi) and abi != "" and
             is_integer(fuel) and fuel > 0 and is_integer(memory) and memory > 0, do: :ok

  def validate(_), do: {:error, :invalid_wasm_runtime_identity}
end
