defmodule ChatGPTCloud.HumanValue.Provider do
  @moduledoc "Deterministic Faker-style acquisition for coherent synthetic economic worlds."

  @provider __MODULE__ |> Atom.to_string()
  @currency "USD"

  def acquire(run_id, seed) when is_binary(run_id) and is_integer(seed) do
    org_token = token(seed, "organization")
    person_token = token(seed, "person")
    opportunity_token = token(seed, "opportunity")

    offer_cents = 100_000 + bounded(seed, "offer", 900_000)
    invoice_cents = div(offer_cents * (70 + bounded(seed, "invoice", 26)), 100)
    payment_cents = div(invoice_cents * (60 + bounded(seed, "payment", 41)), 100)
    value_outcome_cents = payment_cents * (2 + bounded(seed, "value", 4))

    customer_revenue_outcome_cents =
      value_outcome_cents + bounded(seed, "customer-revenue", 250_000)

    acquired_at = DateTime.utc_now()

    %{
      scenario_id: "hv-" <> String.slice(token(seed, "scenario"), 0, 16),
      run_id: run_id,
      provider: @provider,
      seed: seed,
      organization: "organization-" <> String.slice(org_token, 0, 12),
      contact_name: "person-" <> String.slice(person_token, 0, 12),
      contact_email: String.slice(person_token, 0, 16) <> "@synthetic.invalid",
      opportunity: "opportunity-" <> String.slice(opportunity_token, 0, 12),
      offer_cents: offer_cents,
      invoice_cents: invoice_cents,
      payment_cents: payment_cents,
      value_outcome_cents: value_outcome_cents,
      customer_revenue_outcome_cents: customer_revenue_outcome_cents,
      currency: @currency,
      acquired_at: acquired_at,
      synthetic: true
    }
  end

  def next_seed do
    System.unique_integer([:positive, :monotonic])
    |> Kernel.+(System.system_time(:microsecond))
    |> rem(2_000_000_000)
  end

  defp bounded(seed, label, upper_exclusive) do
    <<value::unsigned-integer-size(64), _::binary>> = :crypto.hash(:sha256, "#{seed}:#{label}")
    rem(value, upper_exclusive)
  end

  defp token(seed, label) do
    :crypto.hash(:sha256, "#{seed}:#{label}")
    |> Base.encode16(case: :lower)
  end
end
