defmodule ChatGPTCloudControlPlane.RuntimeContracts.GraphqlProjectionTest do
  use ExUnit.Case, async: true
  alias ChatGPTCloudControlPlane.RuntimeContracts.GraphqlProjection
  test "admits only declared fields" do
    assert :ok = GraphqlProjection.validate(:status, [:status, :receipt])
    assert {:error, :graphql_field_not_exposed} = GraphqlProjection.validate(:delete, [:status, :receipt])
  end
end
