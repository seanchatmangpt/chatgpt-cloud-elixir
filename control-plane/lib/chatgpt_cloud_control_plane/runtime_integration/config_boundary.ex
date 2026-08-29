defmodule ChatGPTCloud.RuntimeIntegration.ConfigBoundary do
  @moduledoc "Separates required runtime configuration from secret-bearing configuration."
  @required [:database_url]

  @spec validate(map()) :: :ok | {:error, {:missing_config, [atom()]}}
  def validate(config) when is_map(config) do
    missing = Enum.reject(@required, &present?(Map.get(config, &1)))
    if missing == [], do: :ok, else: {:error, {:missing_config, missing}}
  end

  defp present?(value), do: is_binary(value) and byte_size(value) > 0
end
