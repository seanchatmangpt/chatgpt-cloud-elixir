defmodule ChatGPTCloud.RuntimeIntegration.ExtensionManifest do
  @moduledoc "Canonical responsibility map for the admitted Ash ecosystem extensions."
  @roles %{
    spark: :compile_time_contracts,
    reactor: :orchestration,
    igniter: :reproducible_manufacture,
    ash_json_api: :machine_projection,
    ash_authentication: :operator_identity,
    ash_oban: :durable_work,
    ash_state_machine: :lifecycle,
    ash_archival: :evidence_retention,
    ash_money: :cost_evidence,
    ash_cloak: :secret_storage,
    ash_graphql: :query_projection,
    ash_ai: :bounded_ai_queries
  }

  @spec role(atom()) :: {:ok, atom()} | {:error, :unknown_extension}
  def role(extension) do
    case Map.fetch(@roles, extension) do
      {:ok, role} -> {:ok, role}
      :error -> {:error, :unknown_extension}
    end
  end
end
