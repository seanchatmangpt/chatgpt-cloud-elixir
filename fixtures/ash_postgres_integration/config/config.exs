import Config

# scripts/build-capsule.sh always generates a mix.exs with `app: :cloud_capsule`
# regardless of which fixture is copied in — this config MUST target that exact
# OTP app name or AshPostgresIntegration.Repo will not find its configuration.
config :cloud_capsule, ecto_repos: [AshPostgresIntegration.Repo]

# Matches the postgres17 capsule's own convention (scripts/postgres-server.sh,
# capsules/postgres17/capsule.toml): 127.0.0.1:55432, trust-auth `postgres`
# user, no password required. Overridable so this also works against a plain
# GitHub Actions `services: postgres:` container on its default port/user.
config :cloud_capsule, AshPostgresIntegration.Repo,
  username: System.get_env("PGUSER", "postgres"),
  password: System.get_env("PGPASSWORD"),
  hostname: System.get_env("PGHOST", "127.0.0.1"),
  port: String.to_integer(System.get_env("PGPORT", "55432")),
  database: System.get_env("PGDATABASE", "ash_postgres_integration"),
  pool_size: 2,
  show_sensitive_data_on_connection_error: true
