defmodule ChatGPTCloud.RuntimeIntegration.PersistenceBoundaryTest do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.RuntimeIntegration.PersistenceBoundary

  test "persistent actions name their repository and transaction mode" do
    assert :ok = PersistenceBoundary.validate(%{repo: ChatGPTCloudControlPlane.Repo, transaction: :required})
    assert {:error, :persistence_repository_required} = PersistenceBoundary.validate(%{transaction: :required})
  end
end
