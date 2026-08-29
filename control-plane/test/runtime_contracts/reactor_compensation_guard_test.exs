defmodule ChatGPTCloudControlPlane.RuntimeContracts.ReactorCompensationGuardTest do
  use ExUnit.Case, async: true
  alias ChatGPTCloudControlPlane.RuntimeContracts.ReactorCompensationGuard

  test "compensation requires failed-step receipt binding" do
    assert :ok = ReactorCompensationGuard.validate(%{failed_step: "ingest", receipt_digest: "abc", compensating_action: :rollback})
    assert {:error, :invalid_compensation_contract} = ReactorCompensationGuard.validate(%{failed_step: "ingest"})
  end
end
