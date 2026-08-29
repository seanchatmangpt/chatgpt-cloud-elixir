# This fixture is never run through scripts/run-offline.sh (which network-namespace-
# isolates its acceptance command on purpose — see capsules/ash-postgres/capsule.toml's
# `external_crowns`). It is only ever invoked by
# scripts/verify-ash-postgres-integration.sh, which requires network and a reachable
# PostgreSQL 17 service and runs `mix ecto.create`/`mix ecto.migrate` before `mix test`.
# The generated mix.exs has no OTP application callback module, so the Repo is started
# directly here rather than via an application supervision tree.
{:ok, _} = Application.ensure_all_started(:postgrex)
{:ok, _} = AshPostgresIntegration.Repo.start_link()

ExUnit.start()
