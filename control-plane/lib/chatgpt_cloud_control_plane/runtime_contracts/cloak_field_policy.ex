defmodule ChatGPTCloudControlPlane.RuntimeContracts.CloakFieldPolicy do
  @moduledoc "Requires secret-bearing resource fields to be encrypted and excluded from receipts."

  @secret_fields [:token, :api_key, :credential, :secret, :private_key]

  def admit(field, %{encrypted: true, receipt_visible: false}) when field in @secret_fields, do: :ok
  def admit(field, _) when field in @secret_fields, do: {:error, {:secret_field_not_cloaked, field}}
  def admit(_, _), do: :ok
end
