defmodule ChatGPTCloud.Repo do
  # ash-functions migrations are not generated for this repo (no atomics/
  # string_trim/ash_elixir_and/ash_elixir_or usage today) -- disable the
  # advisory rather than leave an unaddressed compiler warning under
  # --warnings-as-errors. Revisit (drop this flag, run the migration
  # generator) if a resource action starts needing those.
  use AshPostgres.Repo,
    otp_app: :chatgpt_cloud_control_plane,
    warn_on_missing_ash_functions?: false

  # Matches versions.toml's [services] postgresql_17 = "17.11".
  @impl AshPostgres.Repo
  def min_pg_version, do: %Version{major: 17, minor: 0, patch: 0}
end
