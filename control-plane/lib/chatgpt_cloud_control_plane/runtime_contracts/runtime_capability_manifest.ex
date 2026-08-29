defmodule ChatGPTCloudControlPlane.RuntimeContracts.RuntimeCapabilityManifest do
  @moduledoc "Requires runtime capability manifests to bind owner, version, and responsibility."

  def validate(%{capability: capability, owner: owner, version: version, responsibility: responsibility})
      when is_binary(capability) and capability != "" and is_binary(owner) and owner != "" and
             is_binary(version) and version != "" and is_binary(responsibility) and responsibility != "", do: :ok

  def validate(_), do: {:error, :invalid_runtime_capability_manifest}
end
