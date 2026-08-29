defmodule ChatGPTCloud.RuntimeIntegration.SecretReceiptFilter do
  @moduledoc """Redacts known secret-bearing keys before runtime evidence enters receipts."""

  @secret_keys MapSet.new([:deployment_token, :api_token, :password, :secret, :ciphertext_ref])

  @spec redact(term()) :: term()
  def redact(value) when is_map(value) do
    Map.new(value, fn {key, nested} ->
      if MapSet.member?(@secret_keys, key), do: {key, "[REDACTED]"}, else: {key, redact(nested)}
    end)
  end

  def redact(value) when is_list(value), do: Enum.map(value, &redact/1)
  def redact(value), do: value
end
