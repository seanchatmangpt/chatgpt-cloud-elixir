defmodule ChatGPTCloud.RuntimeIntegration.CostObservation do
  @moduledoc "Metered execution-cost evidence without billing authority."
  @enforce_keys [:amount, :currency, :source]
  defstruct [:amount, :currency, :source, :observed_at]

  @spec new(number(), String.t(), String.t()) :: {:ok, struct()} | {:error, :negative_cost}
  def new(amount, currency, source) when is_number(amount) and amount >= 0,
    do: {:ok, %__MODULE__{amount: amount, currency: currency, source: source}}
  def new(_, _, _), do: {:error, :negative_cost}
end
