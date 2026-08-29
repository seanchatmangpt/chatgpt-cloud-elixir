defmodule ChatGPTCloudControlPlane.RuntimeContracts.SchemaDigestContract do
  @moduledoc "Binds adapter input/output schema identities across the governed runtime boundary."

  def validate(%{input_schema_digest: input, output_schema_digest: output})
      when is_binary(input) and input != "" and is_binary(output) and output != "", do: :ok

  def validate(_), do: {:error, :invalid_schema_digest_contract}
end
