defmodule ChatGPTCloudControlPlane.RuntimeContracts.ApiRefusal do
  @moduledoc "Requires machine-facing refusals to carry typed code, standing, and reason."
  def validate(%{code: code, standing: :refused, reason: reason}) when is_binary(code) and code != "" and is_binary(reason) and reason != "", do: :ok
  def validate(_), do: {:error, :invalid_api_refusal}
end
