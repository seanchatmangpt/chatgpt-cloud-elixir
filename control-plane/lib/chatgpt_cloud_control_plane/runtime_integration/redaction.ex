defmodule ChatGPTCloud.RuntimeIntegration.Redaction do
  @moduledoc "Redacts secret-bearing runtime metadata before receipts leave the authority boundary."

  @secret_names MapSet.new(~w(token api_token password secret credential private_key))

  @spec apply(map()) :: map()
  def apply(map) when is_map(map) do
    Map.new(map, fn {key, value} ->
      if secret_name?(key), do: {key, "[REDACTED]"}, else: {key, value}
    end)
  end

  defp secret_name?(key) when is_atom(key), do: key |> Atom.to_string() |> secret_name?()

  defp secret_name?(key) when is_binary(key),
    do: MapSet.member?(@secret_names, String.downcase(key))

  defp secret_name?(_), do: false
end
