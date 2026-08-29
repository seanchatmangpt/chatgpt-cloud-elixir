defmodule ChatGPTCloud.RuntimeIntegration.Compensation do
  @moduledoc "Explicit compensation descriptors for failed runtime construction."
  @enforce_keys [:step, :action]
  defstruct [:step, :action, :reason]

  @spec required?(map()) :: boolean()
  def required?(%{side_effect: true}), do: true
  def required?(_), do: false
end
