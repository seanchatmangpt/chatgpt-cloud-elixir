defmodule ChatGPTCloud.HumanValue.ProviderTest do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.HumanValue.Provider

  test "two runtime seeds produce distinct coherent economic worlds" do
    first = Provider.acquire("run-provider-test", 101)
    second = Provider.acquire("run-provider-test", 202)

    refute first.scenario_id == second.scenario_id
    refute first.organization == second.organization
    refute first.opportunity == second.opportunity
    refute first.payment_cents == second.payment_cents

    for world <- [first, second] do
      assert world.synthetic
      assert world.provider == "Elixir.ChatGPTCloud.HumanValue.Provider"
      assert world.offer_cents >= world.invoice_cents
      assert world.invoice_cents >= world.payment_cents
      assert world.customer_revenue_outcome_cents >= world.value_outcome_cents
      assert String.ends_with?(world.contact_email, "@synthetic.invalid")
      assert %DateTime{} = world.acquired_at
    end
  end
end
