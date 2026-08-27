defmodule ChatGPTCloud.RuntimeIntegration.ReactorCompensation do
  @moduledoc "Requires compensating operations for side-effecting Reactor steps."

  @spec admit(map()) :: :ok | {:error, :missing_compensation}
  def admit(%{side_effect: true, compensation: compensation}) when not is_nil(compensation), do: :ok
  def admit(%{side_effect: true}), do: {:error, :missing_compensation}
  def admit(_), do: :ok
end
