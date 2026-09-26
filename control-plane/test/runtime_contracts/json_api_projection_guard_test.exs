defmodule ChatGPTCloudControlPlane.RuntimeContracts.JsonApiProjectionGuardTest do
  use ExUnit.Case, async: true
  alias ChatGPTCloudControlPlane.RuntimeContracts.JsonApiProjectionGuard

  test "writes require Ash action authority" do
    assert :ok = JsonApiProjectionGuard.admit(%{mode: :read, resource: "runs"})
    assert {:error, :json_api_write_requires_ash_action} = JsonApiProjectionGuard.admit(%{mode: :write, resource: "runs"})
  end
end
