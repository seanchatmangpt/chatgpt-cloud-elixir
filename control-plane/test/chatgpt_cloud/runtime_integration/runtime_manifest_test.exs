defmodule ChatGPTCloud.RuntimeIntegration.RuntimeManifestTest do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.RuntimeIntegration.RuntimeManifest

  test "complete runtime role closure admits and missing orchestration is explicit" do
    roles = [
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

    assert :ok = RuntimeManifest.verify_roles(roles)

    assert {:error, {:missing_runtime_roles, [:orchestration]}} =
             RuntimeManifest.verify_roles(List.delete(roles, :orchestration))
  end
end
