defmodule ChatGPTCloudControlPlane.RuntimeContracts.CloakedSecret do
  @moduledoc "Refuses plaintext secret-bearing runtime fields."
  def validate(%{encrypted: true, ciphertext: value}) when is_binary(value) and value != "", do: :ok
  def validate(_), do: {:error, :plaintext_secret_refused}
end
