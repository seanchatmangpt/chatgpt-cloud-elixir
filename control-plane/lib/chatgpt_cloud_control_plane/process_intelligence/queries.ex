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
        scalar(
          "SELECT count(*)::bigint FROM ocel_events WHERE ingested_at > now() - interval '60 seconds'"
        ),
      active_agents:
        scalar(
          "SELECT count(*)::bigint FROM ocel_agents WHERE last_seen_at > now() - interval '5 minutes'"
        ),
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

  @fleet_default_window_seconds 300

  @doc """
  Distinct agent lanes with any OCEL event inside the lookback window.
  """
  def lanes_active(opts \\ []) do
    window = window_seconds(opts)

    %{rows: [[count]]} =
      Ecto.Adapters.SQL.query!(
        Repo,
        """
        SELECT count(DISTINCT agent_key)::bigint
        FROM ocel_events
        WHERE occurred_at > now() - interval '1 second' * $1
        """,
        [window]
      )

    count
  end

  @doc """
  Lane latency p50/p95 in seconds, measured as the elapsed time between an
  AgentSpawn and its matching AgentComplete for the same run_key.

  Uses a `lag` window function over the pinned activity set
  ('AgentSpawn','AgentComplete') to pair consecutive lifecycle events per run,
  then `percentile_cont` for the percentile cut.
  """
  def lane_latency(opts \\ []) do
    window = window_seconds(opts)

    result =
      Ecto.Adapters.SQL.query!(
        Repo,
        """
        WITH paired AS (
          SELECT
            run_key,
            EXTRACT(epoch FROM (
              occurred_at - lag(occurred_at) OVER (
              PARTITION BY run_key
              ORDER BY occurred_at, sequence
            ))
          ) AS latency
          FROM ocel_events
          WHERE activity IN ('AgentSpawn', 'AgentComplete')
            AND occurred_at > now() - interval '1 second' * $1
        ),
        spans AS (
          SELECT run_key, latency
          FROM paired
          WHERE latency IS NOT NULL
        )
        SELECT
          coalesce(percentile_cont(0.50) WITHIN GROUP (ORDER BY latency), 0)::float8,
          coalesce(percentile_cont(0.95) WITHIN GROUP (ORDER BY latency), 0)::float8,
          count(*)::bigint
        FROM spans
        """,
        [window]
      )

    [p50, p95, samples] = result.rows |> List.first()

    %{
      p50_seconds: p50,
      p95_seconds: p95,
      samples: samples
    }
  end

  @doc """
  AgentComplete counts grouped by standing inside the lookback window.
  """
  def completions_by_standing(opts \\ []) do
    window = window_seconds(opts)

    result =
      Ecto.Adapters.SQL.query!(
        Repo,
        """
        SELECT standing, count(*)::bigint
        FROM ocel_events
        WHERE activity = 'AgentComplete'
          AND occurred_at > now() - interval '1 second' * $1
        GROUP BY standing
        ORDER BY standing
        """,
        [window]
      )

    Map.new(result.rows, fn [standing, count] -> {standing, count} end)
  end

  @doc """
  Event counts bucketed per minute inside the lookback window. The most
  recent bucket is the trailing partial minute.
  """
  def events_per_minute(opts \\ []) do
    window = window_seconds(opts)

    result =
      Ecto.Adapters.SQL.query!(
        Repo,
        """
        SELECT
          date_trunc('minute', occurred_at)::text AS bucket,
          count(*)::bigint
        FROM ocel_events
        WHERE occurred_at > now() - interval '1 second' * $1
        GROUP BY 1
        ORDER BY 1
        """,
        [window]
      )

    Enum.map(result.rows, fn [bucket, count] ->
      %{minute: bucket, events: count}
    end)
  end

  @doc """
  Aggregated fleet snapshot: active lanes, lane latency percentiles,
  completions by standing, and per-minute event counts.
  """
  def fleet_snapshot(opts \\ []) do
    %{
      window_seconds: window_seconds(opts),
      lanes_active: lanes_active(opts),
      lane_latency: lane_latency(opts),
      completions_by_standing: completions_by_standing(opts),
      events_per_minute: events_per_minute(opts)
    }
  end

  defp window_seconds(opts) do
    Keyword.get(opts, :window_seconds, @fleet_default_window_seconds)
  end

  defp scalar(sql) do
    %{rows: [[value]]} = Ecto.Adapters.SQL.query!(Repo, sql, [])
    value
  end
end
