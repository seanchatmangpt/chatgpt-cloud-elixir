defmodule ChatGPTCloudControlPlane.RuntimeContracts.ReceiptBinding do
  @moduledoc "Requires receipts to bind identity, authority, consequence and replay."
  @required ~w(subject authority consequence replay standing)a
  def validate(receipt) when is_map(receipt) do
    case Enum.find(@required, &(Map.get(receipt, &1) in [nil, ""])) do
      nil -> :ok
      field -> {:error, {:receipt_field_missing, field}}
    end
  end
  def validate(_), do: {:error, :invalid_receipt}
end
