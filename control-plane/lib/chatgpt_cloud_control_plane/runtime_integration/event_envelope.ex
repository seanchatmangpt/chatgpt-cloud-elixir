defmodule ChatGPTCloud.RuntimeIntegration.EventEnvelope do
  @moduledoc "Runtime event envelope with exact subject and observational authority."
  @enforce_keys [:type, :subject, :payload]
  defstruct [:type, :subject, :payload, authority: :observe, occurred_at: nil]

  @spec actuating?(struct()) :: boolean()
  def actuating?(%__MODULE__{authority: authority}), do: authority == :do
end
