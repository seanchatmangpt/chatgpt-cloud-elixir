defmodule AshPostgresIntegration.Repo do
  use AshPostgres.Repo, otp_app: :cloud_capsule

  # No Postgres extensions required: uuid_primary_key values are generated in
  # Elixir (Ash.UUID) at insert time, and the migration's DB-side default uses
  # PostgreSQL 17's built-in gen_random_uuid() (core since PG 13 — no pgcrypto).
  def installed_extensions, do: []
end
