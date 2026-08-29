defmodule ChatGPTCloudControlPlane.RuntimeContracts.ReactorContractTest do
  use ExUnit.Case, async: true
  alias ChatGPTCloudControlPlane.RuntimeContracts.ReactorContract
  test "requires steps rollback and receipt identity" do
    assert :ok = ReactorContract.validate(%{steps: [:ingest, :qualify], rollback: :required, receipt_id: "r1"})
    assert {:error, :reactor_contract_incomplete} = ReactorContract.validate(%{steps: []})
  end
end
