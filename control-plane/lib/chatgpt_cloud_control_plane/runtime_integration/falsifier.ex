defmodule ChatGPTCloud.RuntimeIntegration.Falsifier do
  @moduledoc "Executable falsifier descriptor for runtime integration claims."
  @enforce_keys [:claim, :command, :failure_condition]
  defstruct [:claim, :command, :failure_condition]

  @spec falsified?(struct(), map()) :: boolean()
  def falsified?(%__MODULE__{failure_condition: {:exit_nonzero}}, %{exit_code: code}),
    do: code != 0

  def falsified?(%__MODULE__{failure_condition: {:standing, expected}}, %{standing: actual}),
    do: actual != expected

  def falsified?(_, _), do: false
end
