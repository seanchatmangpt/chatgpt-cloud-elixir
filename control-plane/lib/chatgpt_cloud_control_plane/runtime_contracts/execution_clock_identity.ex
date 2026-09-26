defmodule ChatGPTCloudControlPlane.RuntimeContracts.ExecutionClockIdentity do
  @moduledoc "Binds execution and replay to an explicit clock source and observed timestamp."

  def validate(%{clock: clock, observed_at: %DateTime{}}) when clock in [:system, :monotonic, :fixture], do: :ok
  def validate(_), do: {:error, :invalid_execution_clock_identity}
end
