defmodule ChatGPTCloudControlPlane.RuntimeContracts.MeteredCostTest do
  use ExUnit.Case, async: true
  alias ChatGPTCloudControlPlane.RuntimeContracts.MeteredCost
  test "observes cost without billing authority" do
    assert :ok = MeteredCost.validate(%{amount: 1.25, currency: "USD", billing_authority: false})
    assert {:error, :billing_authority_refused} = MeteredCost.validate(%{billing_authority: true})
  end
end
