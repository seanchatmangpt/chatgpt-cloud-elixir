defmodule ChatGPTCloudControlPlane.RuntimeContracts.ProcessIntelligenceFence do
  @moduledoc "Allows PI consumption only through wasm4pm/wasm4pm-compat ownership."
  @owners ["wasm4pm", "wasm4pm-compat"]
  def validate(owner) when owner in @owners, do: :ok
  def validate(owner), do: {:error, {:process_intelligence_owner_refused, owner}}
end
