defmodule ChatGPTCloudControlPlane.RuntimeContracts.ExecutionModeGuard do
  @moduledoc "Prevents replay/select/construct execution modes from acquiring fresh consequential DO."

  def admit(%{mode: mode, fresh_do: false}) when mode in [:replay, :select, :construct], do: :ok
  def admit(%{mode: :do, authority: :brce}), do: :ok
  def admit(%{mode: mode, fresh_do: true}) when mode in [:replay, :select, :construct], do: {:error, {:fresh_do_refused, mode}}
  def admit(_), do: {:error, :invalid_execution_mode_authority}
end
