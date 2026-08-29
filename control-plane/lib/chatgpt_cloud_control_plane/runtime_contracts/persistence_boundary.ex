defmodule ChatGPTCloudControlPlane.RuntimeContracts.PersistenceBoundary do
  @moduledoc "Requires persistent writes to name the Ash action and transaction boundary."
  def validate(%{action: action, transaction: tx}) when is_atom(action) and tx in [:required, :forbidden, :optional], do: :ok
  def validate(_), do: {:error, :persistence_boundary_missing}
end
