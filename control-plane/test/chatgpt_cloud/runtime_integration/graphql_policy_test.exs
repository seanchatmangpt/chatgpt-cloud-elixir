defmodule ChatGPTCloud.RuntimeIntegration.GraphqlPolicyTest do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.RuntimeIntegration.GraphqlPolicy

  test "query projection is explicit and fail closed" do
    declared = [:read_run, :list_receipts]
    assert GraphqlPolicy.query?(:read_run, declared)
    refute GraphqlPolicy.query?(:delete_run, declared)
  end
end
