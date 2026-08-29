defmodule ChatGPTCloud.RuntimeIntegration.RuntimeManifest do
  @moduledoc "Aggregates the runtime integration invariants for exact-head qualification."

  @required_roles [
    :compile_time_contracts,
    :orchestration,
    :reproducible_manufacture,
    :machine_projection,
    :operator_identity,
    :durable_work,
    :lifecycle,
    :evidence_retention,
    :cost_evidence,
    :secret_storage,
    :query_projection,
    :bounded_ai_queries
  ]

  @spec verify_roles([atom()]) :: :ok | {:error, {:missing_runtime_roles, [atom()]}}
  def verify_roles(roles) do
    missing = @required_roles -- roles
    if missing == [], do: :ok, else: {:error, {:missing_runtime_roles, missing}}
  end
end
