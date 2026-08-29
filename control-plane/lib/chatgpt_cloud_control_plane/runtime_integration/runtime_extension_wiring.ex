defmodule ChatGPTCloud.RuntimeIntegration.RuntimeExtensionWiring do
  @moduledoc """Runtime extension wiring ledger used by Spark-style contract verification."""

  @required %{
    spark: :compile_time_contracts,
    reactor: :orchestration,
    igniter: :manufacture,
    ash_json_api: :json_api,
    ash_authentication: :operator_identity,
    ash_oban: :durable_jobs,
    ash_state_machine: :lifecycle,
    ash_archival: :archival,
    ash_money: :cost_observation,
    ash_cloak: :secret_encryption,
    ash_graphql: :graphql,
    ash_ai: :bounded_ai_reads
  }

  @spec verify(map()) :: :ok | {:error, {:missing_extension_wiring, [atom()]}}
  def verify(wiring) when is_map(wiring) do
    missing = Enum.flat_map(@required, fn {extension, role} -> if Map.get(wiring, extension) == role, do: [], else: [extension] end)
    if missing == [], do: :ok, else: {:error, {:missing_extension_wiring, Enum.sort(missing)}}
  end

  @spec required() :: map()
  def required, do: @required
end
