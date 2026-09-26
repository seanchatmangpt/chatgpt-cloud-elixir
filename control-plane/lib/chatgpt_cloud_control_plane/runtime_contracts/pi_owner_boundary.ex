defmodule ChatGPTCloudControlPlane.RuntimeContracts.PiOwnerBoundary do
  @moduledoc "Enforces wasm4pm/wasm4pm-compat as the only process-intelligence algorithm owners."

  @owners ["wasm4pm", "wasm4pm-compat"]

  def admit(%{owner: owner, capability: capability}) when owner in @owners and is_binary(capability) and capability != "", do: :ok
  def admit(%{owner: owner}), do: {:error, {:process_intelligence_owner_refused, owner}}
  def admit(_), do: {:error, :invalid_process_intelligence_owner}
end
