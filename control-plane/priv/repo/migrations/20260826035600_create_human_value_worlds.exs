defmodule ChatGPTCloud.Repo.Migrations.CreateHumanValueWorlds do
  use Ecto.Migration

  def change do
    create table(:human_value_worlds, primary_key: false) do
      add :id, :uuid, primary_key: true, null: false
      add :scenario_id, :text, null: false
      add :run_id, :text, null: false
      add :provider, :text, null: false
      add :seed, :bigint, null: false
      add :organization, :text, null: false
      add :contact_name, :text, null: false
      add :contact_email, :text, null: false
      add :opportunity, :text, null: false
      add :offer_cents, :bigint, null: false
      add :invoice_cents, :bigint, null: false
      add :payment_cents, :bigint, null: false
      add :value_outcome_cents, :bigint, null: false
      add :customer_revenue_outcome_cents, :bigint, null: false
      add :currency, :text, null: false
      add :synthetic, :boolean, null: false, default: true
      add :status, :text, null: false, default: "acquired"
      add :acquired_at, :utc_datetime_usec, null: false
      add :qualified_at, :utc_datetime_usec
      add :inserted_at, :utc_datetime_usec, null: false, default: fragment("CURRENT_TIMESTAMP")
      add :updated_at, :utc_datetime_usec, null: false, default: fragment("CURRENT_TIMESTAMP")
    end

    create unique_index(:human_value_worlds, [:scenario_id])
    create index(:human_value_worlds, [:run_id, :acquired_at])
  end
end
