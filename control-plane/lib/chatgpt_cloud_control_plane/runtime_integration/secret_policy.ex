defmodule ChatGPTCloud.RuntimeIntegration.SecretPolicy do
  @moduledoc "Classifies secret-bearing fields that must use cloaked storage."
  @secret_fields ~w(token api_token password secret credential private_key)a

  @spec secret?(atom()) :: boolean()
  def secret?(field), do: field in @secret_fields
end
