defmodule ChatGPTCloudControlPlane.RuntimeContracts.Archival do
  @moduledoc "Prevents hard deletion when a resource is governed by archival semantics."
  def validate(:archive), do: :ok
  def validate(:delete), do: {:error, :hard_delete_refused}
  def validate(_), do: {:error, :invalid_archival_operation}
end
