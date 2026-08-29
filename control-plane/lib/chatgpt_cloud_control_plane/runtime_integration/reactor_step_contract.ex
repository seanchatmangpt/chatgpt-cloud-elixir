defmodule ChatGPTCloud.RuntimeIntegration.ReactorStepContract do
  @moduledoc "Explicit input/output and side-effect contract for Reactor steps."
  @enforce_keys [:name, :inputs, :outputs]
  defstruct [:name, :inputs, :outputs, side_effect: false, compensatable: false]

  @spec valid?(struct()) :: boolean()
  def valid?(%__MODULE__{side_effect: true, compensatable: false}), do: false
  def valid?(%__MODULE__{}), do: true
end
