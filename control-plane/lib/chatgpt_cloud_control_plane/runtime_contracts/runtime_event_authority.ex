defmodule ChatGPTCloudControlPlane.RuntimeContracts.RuntimeEventAuthority do
  @moduledoc "Keeps emitted runtime/OCEL events observational; events cannot grant action authority."

  def normalize(event) when is_map(event) do
    event
    |> Map.put(:authority, :observe_only)
    |> Map.delete(:do_granted)
  end

  def normalize(_), do: {:error, :invalid_runtime_event}
end
