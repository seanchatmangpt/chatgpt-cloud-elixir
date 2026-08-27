defmodule ChatGPTCloud.RuntimeIntegration.SparkContract do
  @moduledoc "Compile-time extension wiring contract consumed by Spark-backed verification."
  @required_extensions MapSet.new([:ash_json_api, :ash_graphql, :ash_ai, :ash_state_machine, :ash_archival])

  @spec verify([atom()]) :: :ok | {:error, {:missing_extensions, [atom()]}}
  def verify(extensions) when is_list(extensions) do
    missing = MapSet.difference(@required_extensions, MapSet.new(extensions)) |> MapSet.to_list() |> Enum.sort()
    if missing == [], do: :ok, else: {:error, {:missing_extensions, missing}}
  end
end
