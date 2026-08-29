defmodule ChatGPTCloudControlPlane.RuntimeContracts.InvocationDigest do
  @moduledoc "Binds runtime invocation input and output digests for replay/coherence checks."

  def validate(%{input_digest: input, output_digest: output})
      when is_binary(input) and input != "" and is_binary(output) and output != "", do: :ok

  def validate(_), do: {:error, :invalid_invocation_digest}
end
