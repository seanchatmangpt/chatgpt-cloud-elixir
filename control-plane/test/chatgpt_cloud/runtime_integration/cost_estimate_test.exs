defmodule ChatGPTCloud.RuntimeIntegration.CostEstimateTest do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.RuntimeIntegration.CostEstimate

  test "cost observations admit metered values but refuse billing authority" do
    assert :ok = CostEstimate.admit(%CostEstimate{amount_minor: 125, currency: "USD", kind: :metered})
    assert {:error, :billing_authority_refused} = CostEstimate.admit(%CostEstimate{amount_minor: 125, currency: "USD", kind: :metered, authority: :bill})
  end
end
