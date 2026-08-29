defmodule ChatGPTCloud.RuntimeIntegration.ReactorExecutionPlanTest do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.RuntimeIntegration.ReactorExecutionPlan

  test "execution plan is ordered unique and bounded" do
    assert :ok = ReactorExecutionPlan.admit(%ReactorExecutionPlan{steps: [:ingest, :conform, :qualify, :replay]})
    assert {:error, :invalid_reactor_plan} = ReactorExecutionPlan.admit(%ReactorExecutionPlan{steps: [:ingest, :ingest]})
    assert {:error, :invalid_reactor_plan} = ReactorExecutionPlan.admit(%ReactorExecutionPlan{steps: [:deploy]})
  end
end
