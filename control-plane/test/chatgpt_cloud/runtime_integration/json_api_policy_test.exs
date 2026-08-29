defmodule ChatGPTCloud.RuntimeIntegration.JsonApiPolicyTest do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.RuntimeIntegration.JsonApiPolicy

  test "reads may project while mutations require explicit declaration" do
    assert JsonApiPolicy.exposed?(:read, [:read, :create])
    assert JsonApiPolicy.exposed?(:create, [:read, :create])
    refute JsonApiPolicy.exposed?(:destroy, [:read, :create])
  end
end
