defmodule ChatGPTCloudControlPlane.RuntimeContracts.PersistenceBoundaryTest do
  use ExUnit.Case, async: true
  alias ChatGPTCloudControlPlane.RuntimeContracts.PersistenceBoundary
  test "requires action and transaction semantics" do
    assert :ok = PersistenceBoundary.validate(%{action: :ingest, transaction: :required})
    assert {:error, :persistence_boundary_missing} = PersistenceBoundary.validate(%{action: :ingest})
  end
end
