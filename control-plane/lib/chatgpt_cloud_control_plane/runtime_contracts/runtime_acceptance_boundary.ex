defmodule ChatGPTCloudControlPlane.RuntimeContracts.RuntimeAcceptanceBoundary do
  @moduledoc "Requires acceptance evidence to bind the requested boundary rather than a weaker substitute."

  @rank %{inspect: 0, compile: 1, unit: 2, integration: 3, e2e: 4, capsule: 5}

  def admit(required, observed) when is_map_key(@rank, required) and is_map_key(@rank, observed) do
    if Map.fetch!(@rank, observed) >= Map.fetch!(@rank, required), do: :ok, else: {:error, {:insufficient_acceptance_boundary, required, observed}}
  end

  def admit(_, _), do: {:error, :invalid_acceptance_boundary}
end
