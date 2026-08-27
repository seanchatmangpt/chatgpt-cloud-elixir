defmodule ChatGPTCloud.RuntimeIntegration.CostObservationTest do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.RuntimeIntegration.CostObservation

  test "cost evidence accepts non-negative observations and refuses negative values" do
    assert {:ok, observation} = CostObservation.new(1.25, "USD", "runtime-meter")
    assert observation.amount == 1.25
    assert observation.currency == "USD"
    assert {:error, :negative_cost} = CostObservation.new(-0.01, "USD", "runtime-meter")
  end
end
