defmodule ChatGPTCloudControlPlane.RuntimeContracts.InvocationReceipt do
  @moduledoc "Binds governed invocation receipts to adapter, runtime, policy, subject, and IO identity."

  @required ~w(subject_sha adapter_digest runtime_digest policy_digest input_digest output_digest)a

  def validate(receipt) when is_map(receipt) do
    case Enum.find(@required, &(Map.get(receipt, &1) in [nil, ""])) do
      nil -> :ok
      field -> {:error, {:missing_invocation_receipt_field, field}}
    end
  end

  def validate(_), do: {:error, :invalid_invocation_receipt}
end
