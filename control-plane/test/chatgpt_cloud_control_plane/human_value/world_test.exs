defmodule ChatGPTCloud.HumanValue.WorldTest do
  use ChatGPTCloud.DataCase, async: false

  alias ChatGPTCloud.HumanValue.{Provider, World}

  test "dynamic acquisition becomes an Ash record with dual revenue calculations" do
    attrs = Provider.acquire("run-ash-test", 303)

    world =
      World
      |> Ash.Changeset.for_create(:acquire, attrs)
      |> Ash.create!()
      |> Ash.load!([:revenue_from_customer_cents, :revenue_for_customer_cents])

    assert world.scenario_id == attrs.scenario_id
    assert world.revenue_from_customer_cents == attrs.payment_cents
    assert world.revenue_for_customer_cents == attrs.customer_revenue_outcome_cents
    assert world.status == :acquired
    assert world.synthetic

    qualified =
      world
      |> Ash.Changeset.for_update(:qualify, %{status: :qualified, qualified_at: DateTime.utc_now()})
      |> Ash.update!()

    assert qualified.status == :qualified
    assert %DateTime{} = qualified.qualified_at
  end

  test "Ash rejects nonpositive purported value before it reaches Phoenix" do
    attrs = Provider.acquire("run-invalid-test", 404) |> Map.put(:payment_cents, 0)

    result =
      World
      |> Ash.Changeset.for_create(:acquire, attrs)
      |> Ash.create()

    assert {:error, _} = result
  end
end
