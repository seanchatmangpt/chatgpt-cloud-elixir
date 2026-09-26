defmodule ChatGPTCloudControlPlane.RuntimeContracts.ApiToken do
  @moduledoc "Validates token metadata without admitting raw credentials into receipts."

  def validate(%{token_id: id, digest: digest}) when is_binary(id) and id != "" and is_binary(digest) and byte_size(digest) >= 32, do: :ok
  def validate(_), do: {:error, :api_token_identity_missing}
end
