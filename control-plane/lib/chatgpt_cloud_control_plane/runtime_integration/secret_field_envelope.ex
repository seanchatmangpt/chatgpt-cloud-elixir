defmodule ChatGPTCloud.RuntimeIntegration.SecretFieldEnvelope do
  @moduledoc """Metadata-only envelope for encrypted secret-bearing fields; plaintext never enters receipts."""

  @enforce_keys [:field, :ciphertext_ref, :key_version]
  defstruct [:field, :ciphertext_ref, :key_version]

  @type t :: %__MODULE__{field: atom(), ciphertext_ref: String.t(), key_version: pos_integer()}

  @spec admit(t()) :: :ok | {:error, :invalid_secret_envelope}
  def admit(%__MODULE__{field: field, ciphertext_ref: ref, key_version: version})
      when is_atom(field) and is_binary(ref) and ref != "" and is_integer(version) and version > 0,
      do: :ok

  def admit(_), do: {:error, :invalid_secret_envelope}

  @spec receipt_projection(t()) :: map()
  def receipt_projection(%__MODULE__{field: field, key_version: version}), do: %{field: field, encrypted: true, key_version: version}
end
