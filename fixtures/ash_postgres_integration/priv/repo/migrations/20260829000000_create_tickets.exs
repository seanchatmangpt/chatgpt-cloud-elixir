defmodule AshPostgresIntegration.Repo.Migrations.CreateTickets do
  use Ecto.Migration

  def change do
    create table(:tickets, primary_key: false) do
      add :id, :uuid, primary_key: true, null: false, default: fragment("gen_random_uuid()")
      add :name, :text, null: false
      add :score, :integer, null: false, default: 0
    end

    create unique_index(:tickets, [:name])
  end
end
