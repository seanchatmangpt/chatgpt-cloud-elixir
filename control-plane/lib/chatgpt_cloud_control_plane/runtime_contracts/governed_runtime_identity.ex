defmodule ChatGPTCloudControlPlane.RuntimeContracts.GovernedRuntimeIdentity do
  @moduledoc "Binds runtime implementation identity, version, digest, and execution substrate."

  def validate(%{runtime: runtime, version: version, digest: digest, substrate: substrate})
      when is_binary(runtime) and runtime != "" and is_binary(version) and version != "" and
             is_binary(digest) and digest != "" and substrate in [:beam, :wasm, :external_process], do: :ok

  def validate(_), do: {:error, :invalid_governed_runtime_identity}
end
