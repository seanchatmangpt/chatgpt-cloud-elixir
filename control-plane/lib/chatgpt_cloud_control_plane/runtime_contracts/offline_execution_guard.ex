defmodule ChatGPTCloudControlPlane.RuntimeContracts.OfflineExecutionGuard do
  @moduledoc "Rejects hidden network dependency when a runtime operation declares offline execution."

  def admit(%{mode: :offline, network_fetches: 0}), do: :ok
  def admit(%{mode: :offline, network_fetches: count}) when is_integer(count) and count > 0, do: {:error, {:offline_network_fetch_refused, count}}
  def admit(%{mode: :online}), do: :ok
  def admit(_), do: {:error, :invalid_execution_mode}
end
