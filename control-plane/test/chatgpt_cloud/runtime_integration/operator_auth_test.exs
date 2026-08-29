defmodule ChatGPTCloud.RuntimeIntegration.OperatorAuthTest do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.RuntimeIntegration.OperatorAuth

  test "operator access requires a non-empty authenticated identity" do
    assert :ok = OperatorAuth.authorize(%{operator_id: "operator-1"})
    assert {:error, :operator_authentication_required} = OperatorAuth.authorize(%{})
    assert {:error, :operator_authentication_required} = OperatorAuth.authorize(%{operator_id: ""})
  end
end
