defmodule ChatGPTCloudControlPlane.RuntimeContracts.ReceiptRedactionPolicy do
  @moduledoc "Recursively removes secret-bearing keys before runtime evidence is serialized."

  @secret_keys ~w(token api_key credential secret private_key authorization)a

  def redact(map) when is_map(map) do
    Map.new(map, fn {key, value} -> {key, redact_value(key, value)} end)
    |> Map.drop(@secret_keys)
  end

  def redact(value), do: value

  defp redact_value(key, _) when key in @secret_keys, do: "[REDACTED]"
  defp redact_value(_, value) when is_map(value), do: redact(value)
  defp redact_value(_, value) when is_list(value), do: Enum.map(value, &redact/1)
  defp redact_value(_, value), do: value
end
