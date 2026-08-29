defmodule ChatGPTCloudControlPlane.RuntimeContracts.RuntimeCapabilityAdmission do
  @moduledoc "Admits runtime capabilities only when responsibility, owner, and verifier are explicit."

  def admit(%{capability: capability, owner: owner, verifier: verifier})
      when is_binary(capability) and capability != "" and is_binary(owner) and owner != "" and is_binary(verifier) and verifier != "", do: :ok

  def admit(_), do: {:error, :invalid_runtime_capability_admission}
end
