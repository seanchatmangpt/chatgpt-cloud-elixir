defmodule ChatGPTCloudControlPlane.RuntimeContracts.ReceiptIoCoherence do
  @moduledoc "Requires receipt IO digests to match the invocation IO digests they attest."

  def validate(%{receipt_input: input, invocation_input: input, receipt_output: output, invocation_output: output})
      when is_binary(input) and input != "" and is_binary(output) and output != "", do: :ok

  def validate(_), do: {:error, :receipt_io_mismatch}
end
