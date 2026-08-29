defmodule ChatGPTCloud.RuntimeIntegration.CostAuthorityTest do
  use ExUnit.Case, async: true
  alias ChatGPTCloud.RuntimeIntegration.{CostAuthority, CostObservation}

  test "cost observations are evidence and cannot grant billing authority" do
    assert {:ok, observation} = CostObservation.new(1.25, "USD", "runtime-estimate")
    assert observation.amount == 1.25
    assert :ok = CostAuthority.admit(%{billing_authority: false})

    assert {:error, :billing_authority_forbidden} =
             CostAuthority.admit(%{billing_authority: true})
  end
end
