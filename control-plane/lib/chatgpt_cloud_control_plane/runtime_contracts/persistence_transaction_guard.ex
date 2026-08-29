defmodule ChatGPTCloudControlPlane.RuntimeContracts.PersistenceTransactionGuard do
  @moduledoc "Requires multi-resource runtime writes to declare transactional scope and rollback behavior."

  def admit(%{resources: resources, transactional: true, rollback: rollback})
      when is_list(resources) and length(resources) > 1 and rollback in [:automatic, :reactor_compensation], do: :ok
  def admit(%{resources: [_]}), do: :ok
  def admit(_), do: {:error, :unsafe_persistence_transaction}
end
