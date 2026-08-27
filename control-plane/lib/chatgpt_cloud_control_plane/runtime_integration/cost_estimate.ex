defmodule ChatGPTCloud.RuntimeIntegration.CostEstimate do
  @moduledoc """Metered or estimated execution cost as observation, never billing authority."""

  @enforce_keys [:amount_minor, :currency, :kind]
  defstruct [:amount_minor, :currency, :kind, authority: :observe]

  @type t :: %__MODULE__{
          amount_minor: non_neg_integer(),
          currency: String.t(),
          kind: :metered | :estimated,
          authority: :observe | atom()
        }

  @spec admit(t()) :: :ok | {:error, atom()}
  def admit(%__MODULE__{amount_minor: amount, currency: currency, kind: kind, authority: :observe})
      when is_integer(amount) and amount >= 0 and is_binary(currency) and byte_size(currency) == 3 and kind in [:metered, :estimated],
      do: :ok

  def admit(%__MODULE__{authority: _}), do: {:error, :billing_authority_refused}
  def admit(_), do: {:error, :invalid_cost_estimate}
end
