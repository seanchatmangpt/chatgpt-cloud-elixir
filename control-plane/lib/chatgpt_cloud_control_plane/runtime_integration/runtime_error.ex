defmodule ChatGPTCloud.RuntimeIntegration.RuntimeError do
  @moduledoc "Typed runtime integration errors that preserve refusal and blocker semantics."
  defexception [:type, :reason, :details]

  @spec new(atom(), atom(), map()) :: struct()
  def new(type, reason, details \\ %{}) when type in [:refused, :blocked, :build_broken],
    do: %__MODULE__{type: type, reason: reason, details: details}

  @impl true
  def message(%__MODULE__{type: type, reason: reason}), do: "#{type}:#{reason}"
end
