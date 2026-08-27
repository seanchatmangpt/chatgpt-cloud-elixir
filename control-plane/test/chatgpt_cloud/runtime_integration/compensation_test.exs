defmodule ChatGPTCloud.RuntimeIntegration.CompensationTest do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.RuntimeIntegration.Compensation

  test "side-effecting construction requires an explicit compensation path" do
    assert Compensation.required?(%{side_effect: true})
    refute Compensation.required?(%{side_effect: false})
    refute Compensation.required?(%{})
  end
end
