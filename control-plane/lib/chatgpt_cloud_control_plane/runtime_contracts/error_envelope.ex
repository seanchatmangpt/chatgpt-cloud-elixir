defmodule ChatGPTCloudControlPlane.RuntimeContracts.ErrorEnvelope do
  @moduledoc "Manufactures typed machine-readable runtime errors without leaking secret-bearing detail."

  def build(code, message, metadata \\ %{}) when is_atom(code) and is_binary(message) and is_map(metadata) do
    {:ok, %{code: code, message: message, metadata: Map.drop(metadata, [:token, :api_key, :credential, :secret, :private_key])}}
  end

  def build(_, _, _), do: {:error, :invalid_error_envelope}
end
