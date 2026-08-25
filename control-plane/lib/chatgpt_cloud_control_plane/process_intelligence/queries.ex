defmodule ChatGPTCloud.ProcessIntelligence.Queries do
  @moduledoc false
  alias ChatGPTCloud.Repo

  def recent_events(limit \\ 200) do
    result =
      Ecto.Adapters.SQL.query!(
        Repo,
        """
        SELECT id::text, event_key, agent_key, run_key, activity, lifecycle,
               sequence, standing, authority_domain, occurred_at, ingested_at,
               digest, previous_digest, payload
        FROM ocel_events
        ORDER BY occurred_at DESC, sequence DESC
        LIMIT $1
        """,
        [limit]
      )

    Enum.map(result.rows, fn row ->
      result.columns
      |> Enum.zip(row)
      |> Map.new(fn {key, value} -> {String.to_atom(key), value} end)
    end)
  end

  def stats do
    %{
      events_last_minute:
        scalar("SELECT count(*)::bigint FROM ocel_events WHERE ingested_at > now() - interval '60 seconds'"),
      active_agents:
        scalar("SELECT count(*)::bigint FROM ocel_agents WHERE last_seen_at > now() - interval '5 minutes'"),
      active_runs:
        scalar(
          "SELECT count(*)::bigint FROM ocel_runs WHERE ended_at IS NULL AND last_seen_at > now() - interval '5 minutes'"
        ),
      refusals_last_hour:
        scalar(
          "SELECT count(*)::bigint FROM ocel_refusals WHERE observed_at > now() - interval '60 minutes'"
        ),
      process_variants: scalar("SELECT count(*)::bigint FROM ocel_process_variants")
    }
  end

  defp scalar(sql) do
    %{rows: [[value]]} = Ecto.Adapters.SQL.query!(Repo, sql, [])
    value
  end
end
