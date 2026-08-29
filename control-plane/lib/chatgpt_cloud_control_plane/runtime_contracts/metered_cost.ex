defmodule ChatGPTCloudControlPlane.RuntimeContracts.MeteredCost do
  @moduledoc "Allows cost observation while refusing implicit billing authority."
  def validate(%{amount: amount, currency: currency, billing_authority: false}) when is_number(amount) and amount >= 0 and is_binary(currency), do: :ok
  def validate(%{billing_authority: true}), do: {:error, :billing_authority_refused}
  def validate(_), do: {:error, :invalid_metered_cost}
end
