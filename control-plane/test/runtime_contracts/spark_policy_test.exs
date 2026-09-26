defmodule ChatGPTCloudControlPlane.RuntimeContracts.SparkPolicyTest do
  use ExUnit.Case, async: true
  alias ChatGPTCloudControlPlane.RuntimeContracts.SparkPolicy
  test "requires standing and authority domains" do
    assert :ok = SparkPolicy.validate(%{standing_domain: :runtime, authority_domain: :github})
    assert {:error, :spark_policy_incomplete} = SparkPolicy.validate(%{standing_domain: :runtime})
  end
end
