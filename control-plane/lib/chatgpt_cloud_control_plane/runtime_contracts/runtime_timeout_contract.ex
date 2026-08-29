defmodule ChatGPTCloudControlPlane.RuntimeContracts.RuntimeTimeoutContract do
  @moduledoc "Requires positive finite runtime timeout budgets for governed adapter invocations."

  def validate(%{timeout_ms: timeout}) when is_integer(timeout) and timeout > 0 and timeout <= 3_600_000, do: :ok
  def validate(%{timeout_ms: timeout}), do: {:error, {:invalid_runtime_timeout, timeout}}
  def validate(_), do: {:error, :missing_runtime_timeout}
end
