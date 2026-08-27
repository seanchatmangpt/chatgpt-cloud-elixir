defmodule ChatGPTCloudControlPlane.RuntimeContracts.RuntimeReceiptIdentity do
  @moduledoc "Requires runtime receipts to bind repo/ref/SHA, command, exit, and replay identity."

  @required ~w(repo ref sha command replay_id)a

  def validate(receipt) when is_map(receipt) do
    missing = Enum.find(@required, &(Map.get(receipt, &1) in [nil, ""]))
    cond do
      missing -> {:error, {:missing_runtime_receipt_field, missing}}
      not is_integer(Map.get(receipt, :exit)) -> {:error, :missing_runtime_exit}
      true -> :ok
    end
  end

  def validate(_), do: {:error, :invalid_runtime_receipt}
end
