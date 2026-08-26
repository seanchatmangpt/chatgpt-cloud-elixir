defmodule ChatGPTCloud.HumanValue.World do
  @moduledoc "A synthetic runtime world whose economic values are acquired dynamically and receipted."

  use Ash.Resource,
    otp_app: :chatgpt_cloud_control_plane,
    domain: ChatGPTCloud.HumanValue,
    data_layer: AshPostgres.DataLayer,
    authorizers: [Ash.Policy.Authorizer]

  postgres do
    table "human_value_worlds"
    repo ChatGPTCloud.Repo
  end

  actions do
    defaults [:read]

    create :acquire do
      primary? true

      accept [
        :scenario_id,
        :run_id,
        :provider,
        :seed,
        :organization,
        :contact_name,
        :contact_email,
        :opportunity,
        :offer_cents,
        :invoice_cents,
        :payment_cents,
        :value_outcome_cents,
        :customer_revenue_outcome_cents,
        :currency,
        :acquired_at,
        :synthetic
      ]

      validate compare(:offer_cents, greater_than: 0)
      validate compare(:invoice_cents, greater_than: 0)
      validate compare(:payment_cents, greater_than: 0)
      validate compare(:value_outcome_cents, greater_than: 0)
      validate compare(:customer_revenue_outcome_cents, greater_than: 0)
    end

    update :qualify do
      accept [:status, :qualified_at]
    end
  end

  policies do
    policy action_type(:read) do
      authorize_if always()
    end

    policy action([:acquire, :qualify]) do
      authorize_if always()
    end
  end

  attributes do
    uuid_primary_key :id

    attribute :scenario_id, :string, allow_nil?: false, public?: true
    attribute :run_id, :string, allow_nil?: false, public?: true
    attribute :provider, :string, allow_nil?: false, public?: true
    attribute :seed, :integer, allow_nil?: false, public?: true
    attribute :organization, :string, allow_nil?: false, public?: true
    attribute :contact_name, :string, allow_nil?: false, public?: true
    attribute :contact_email, :string, allow_nil?: false, public?: true
    attribute :opportunity, :string, allow_nil?: false, public?: true
    attribute :offer_cents, :integer, allow_nil?: false, public?: true
    attribute :invoice_cents, :integer, allow_nil?: false, public?: true
    attribute :payment_cents, :integer, allow_nil?: false, public?: true
    attribute :value_outcome_cents, :integer, allow_nil?: false, public?: true
    attribute :customer_revenue_outcome_cents, :integer, allow_nil?: false, public?: true
    attribute :currency, :string, allow_nil?: false, public?: true
    attribute :synthetic, :boolean, allow_nil?: false, default: true, public?: true

    attribute :status, :atom,
      allow_nil?: false,
      default: :acquired,
      constraints: [one_of: [:acquired, :qualified]],
      public?: true

    attribute :acquired_at, :utc_datetime_usec, allow_nil?: false, public?: true
    attribute :qualified_at, :utc_datetime_usec, public?: true

    create_timestamp :inserted_at
    update_timestamp :updated_at
  end

  calculations do
    calculate :revenue_from_customer_cents, :integer, expr(payment_cents), public?: true

    calculate :revenue_for_customer_cents, :integer, expr(customer_revenue_outcome_cents),
      public?: true
  end

  identities do
    identity :unique_scenario, [:scenario_id]
  end
end
