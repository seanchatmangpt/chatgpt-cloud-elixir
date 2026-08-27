defmodule ChatGPTCloud.RuntimeIntegration.Redaction do
  @moduledoc "Redacts secret-bearing runtime metadata before receipts leave the authority boundary."
  alias ChatGPTCloud.RuntimeIntegration.SecretPolicy

  @spec apply(map()) :: map()
  def apply(map) when is_map(map) do
    Map.new(map, fn {key, value} -> if SecretPolicy.secret?(normalize_key(key)), do: {key, "[REDACTED]"}, else: {key, value} end)
  end

  defp normalize_key(key) when is_atom(key), do: key
  defp normalize_key(key) when is_binary(key), do: key |> String.downcase() |> String.to_atom()
end
