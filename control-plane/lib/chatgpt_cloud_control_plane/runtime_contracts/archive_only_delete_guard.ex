defmodule ChatGPTCloudControlPlane.RuntimeContracts.ArchiveOnlyDeleteGuard do
  @moduledoc "Refuses hard deletion for process artifacts that require archival lineage."

  @protected [:ocel_event, :qualification_receipt, :replay_receipt, :process_artifact]

  def admit(resource, :archive) when resource in @protected, do: :ok
  def admit(resource, :delete) when resource in @protected, do: {:error, {:hard_delete_refused, resource}}
  def admit(_, operation) when operation in [:archive, :delete], do: :ok
  def admit(_, _), do: {:error, :invalid_delete_operation}
end
