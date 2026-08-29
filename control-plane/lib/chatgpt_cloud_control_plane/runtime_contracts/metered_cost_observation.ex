defmodule ChatGPTCloudControlPlane.RuntimeContracts.MeteredCostObservation do
  @moduledoc "Represents estimated execution cost as observation only; billing authority is never implied."

  def build(amount, currency) when is_number(amount) and amount >= 0 and is_binary(currency) and byte_size(currency) == 3 do
    {:ok, %{amount: amount, currency: String.upcase(currency), authority: :observe_only}}
  end

  def build(_, _), do: {:error, :invalid_metered_cost}
end
