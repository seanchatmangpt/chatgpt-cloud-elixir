defmodule ChatGPTCloudControlPlane.RuntimeContracts.JsonApiProjectionTest do
  use ExUnit.Case, async: true
  alias ChatGPTCloudControlPlane.RuntimeContracts.JsonApiProjection
  test "exposes only declared actions" do
    allowed = %{run: [:read, :create]}
    assert :ok = JsonApiProjection.validate(:run, :read, allowed)
    assert {:error, :json_api_action_not_exposed} = JsonApiProjection.validate(:run, :destroy, allowed)
  end
end
