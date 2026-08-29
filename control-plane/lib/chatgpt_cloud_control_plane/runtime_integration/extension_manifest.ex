defmodule ChatGPTCloud.RuntimeIntegration.ExtensionManifest do
  @moduledoc """
  Canonical responsibility map for the admitted Ash ecosystem extensions.

  :ash_authentication (role :operator_identity) was removed 2026-08-29: zero real
  use/DSL/router usage anywhere in the app (real auth is hand-rolled Basic/bearer
  plugs, ChatGPTCloudWeb.AdminAuth/OcelAuth) -- it only ever existed here as a
  Code.ensure_loaded?/1 check in ChatGPTCloud.Ecosystem.receipt/0, giving false
  confidence that "operator identity" was a real, exercised capability. See
  docs/errc-tracker.md's Resolved entry for the corresponding ecosystem.ex/mix.exs
  changes and ChatGPTCloud.RuntimeIntegration.RuntimeManifest's matching removal.
  """
  @roles %{
    spark: :compile_time_contracts,
    reactor: :orchestration,
    igniter: :reproducible_manufacture,
    ash_json_api: :machine_projection,
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
