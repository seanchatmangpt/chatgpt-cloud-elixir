defmodule ChatGPTCloud.RuntimeIntegration.LifecycleGuard do
  @moduledoc "Fail-closed lifecycle transition admission."
  alias ChatGPTCloud.RuntimeIntegration.Lifecycle

  @spec admit(atom(), atom()) :: :ok | {:error, {:invalid_transition, atom(), atom()}}
  def admit(from, to) do
    if Lifecycle.allowed?(from, to), do: :ok, else: {:error, {:invalid_transition, from, to}}
  end
end
