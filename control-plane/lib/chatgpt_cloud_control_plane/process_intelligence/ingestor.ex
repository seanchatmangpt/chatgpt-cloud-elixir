defmodule ChatGPTCloud.ProcessIntelligence.Ingestor do
  @moduledoc """
  Idempotent ingestion boundary for `chatgpt-cloud-ocel/1` envelopes.

  The producer remains authoritative for event identity and ordering. The control
  plane persists the observation, refuses malformed envelopes, and broadcasts
  only newly admitted events to the LiveView projection.
  """

  alias ChatGPTCloud.Repo

  @schema "chatgpt-cloud-ocel/1"
  @standings ~w(UNKNOWN PARTIAL_ALIVE ALIVE BLOCKED BUILD_BROKEN UNSUPPORTED)

  def ingest(envelope) when is_map(envelope) do
    with {:ok, normalized} <- normalize(envelope),
         {:ok, result} <- persist(normalized) do
      broadcast(result.events)
      {:ok, Map.drop(result, [:events])}
    end
  end

  def ingest(_), do: {:error, :invalid_envelope}

  defp normalize(%{"schema" => @schema, "producer" => producer} = envelope)
       when is_map(producer) do
    with {:ok, agent_key} <- required_string(producer, "agent_id"),
         {:ok, run_key} <- required_string(producer, "run_id"),
         {:ok, events} <- normalize_events(Map.get(envelope, "events", []), agent_key, run_key),
         {:ok, objects} <- normalize_objects(Map.get(envelope, "objects", [])),
         {:ok, relationships} <-
           normalize_object_relationships(Map.get(envelope, "object_relationships", [])),
         {:ok, receipts} <- normalize_receipts(Map.get(envelope, "receipts", []), run_key),
         {:ok, conformance} <-
           normalize_conformance(Map.get(envelope, "conformance_results", []), run_key),
         {:ok, refusals} <- normalize_refusals(Map.get(envelope, "refusals", []), run_key),
         {:ok, variants} <- normalize_variants(Map.get(envelope, "process_variants", [])) do
      now = DateTime.utc_now()

      {:ok,
       %{
         agent: %{
           id: Ecto.UUID.bingenerate(),
           agent_key: agent_key,
           first_seen_at: now,
           last_seen_at: now,
           metadata: Map.get(producer, "metadata", %{}),
           inserted_at: now,
           updated_at: now
         },
         run: %{
           id: Ecto.UUID.bingenerate(),
           run_key: run_key,
           agent_key: agent_key,
           status: Map.get(producer, "status", "running"),
           subject_repo: producer["subject_repo"],
           subject_sha: producer["subject_sha"],
           started_at: parse_timestamp_or_now(producer["started_at"], now),
           last_seen_at: now,
           ended_at: parse_optional_timestamp(producer["ended_at"]),
           metadata: Map.get(producer, "metadata", %{}),
           inserted_at: now,
           updated_at: now
         },
         events: events,
         objects: merge_objects(objects, events),
         event_objects: event_object_rows(events),
         object_relationships: relationships,
         receipts: receipts,
         conformance_results: conformance,
         refusals: refusals,
         process_variants: variants
       }}
    end
  end

  defp normalize(%{"schema" => _}), do: {:error, :unsupported_schema}
  defp normalize(_), do: {:error, :invalid_envelope}

  defp persist(data) do
    Repo.transaction(fn ->
      upsert_agent(data.agent)
      upsert_run(data.run)
      upsert_objects(data.objects)
      insert_object_relationships(data.object_relationships)
      inserted_events = insert_events(data.events)
      insert_event_objects(data.event_objects)
      insert_receipts(data.receipts)
      insert_conformance(data.conformance_results)
      insert_refusals(data.refusals)
      upsert_variants(data.process_variants)

      %{
        accepted_events: length(inserted_events),
        duplicate_events: length(data.events) - length(inserted_events),
        events: inserted_events,
        run_key: data.run.run_key,
        agent_key: data.agent.agent_key,
        standing: "ALIVE"
      }
    end)
  end

  defp upsert_agent(row) do
    Repo.insert_all("ocel_agents", [row],
      on_conflict: {:replace, [:last_seen_at, :metadata, :updated_at]},
      conflict_target: [:agent_key]
    )
  end

  defp upsert_run(row) do
    Repo.insert_all("ocel_runs", [row],
      on_conflict:
        {:replace,
         [
           :agent_key,
           :status,
           :subject_repo,
           :subject_sha,
           :last_seen_at,
           :ended_at,
           :metadata,
           :updated_at
         ]},
      conflict_target: [:run_key]
    )
  end

  defp upsert_objects([]), do: {0, nil}

  defp upsert_objects(rows) do
    Repo.insert_all("ocel_objects", rows,
      on_conflict: {:replace, [:object_type, :label, :attributes, :last_seen_at, :updated_at]},
      conflict_target: [:object_key]
    )
  end

  defp insert_events([]), do: []

  defp insert_events(rows) do
    {_count, returned} =
      Repo.insert_all("ocel_events", Enum.map(rows, &Map.drop(&1, [:objects])),
        on_conflict: :nothing,
        conflict_target: [:event_key],
        returning: [
          :id,
          :event_key,
          :agent_key,
          :run_key,
          :activity,
          :lifecycle,
          :sequence,
          :standing,
          :authority_domain,
          :occurred_at,
          :ingested_at,
          :digest,
          :previous_digest,
          :payload
        ]
      )

    returned || []
  end

  defp insert_event_objects([]), do: {0, nil}

  defp insert_event_objects(rows) do
    Repo.insert_all("ocel_event_objects", rows,
      on_conflict: :nothing,
      conflict_target: [:event_key, :object_key, :qualifier]
    )
  end

  defp insert_object_relationships([]), do: {0, nil}

  defp insert_object_relationships(rows) do
    Repo.insert_all("ocel_object_objects", rows,
      on_conflict: :nothing,
      conflict_target: [:source_object_key, :target_object_key, :qualifier]
    )
  end

  defp insert_receipts([]), do: {0, nil}

  defp insert_receipts(rows) do
    Repo.insert_all("ocel_receipts", rows,
      on_conflict: :nothing,
      conflict_target: [:receipt_key]
    )
  end

  defp insert_conformance([]), do: {0, nil}

  defp insert_conformance(rows) do
    Repo.insert_all("ocel_conformance_results", rows,
      on_conflict: :nothing,
      conflict_target: [:result_key]
    )
  end

  defp insert_refusals([]), do: {0, nil}

  defp insert_refusals(rows) do
    Repo.insert_all("ocel_refusals", rows,
      on_conflict: :nothing,
      conflict_target: [:refusal_key]
    )
  end

  defp upsert_variants([]), do: {0, nil}

  defp upsert_variants(rows) do
    Repo.insert_all("ocel_process_variants", rows,
      on_conflict:
        {:replace, [:name, :model_type, :model_digest, :payload, :last_seen_at, :updated_at]},
      conflict_target: [:variant_key]
    )
  end

  defp normalize_events(events, agent_key, run_key) when is_list(events) do
    Enum.reduce_while(events, {:ok, []}, fn event, {:ok, acc} ->
      case normalize_event(event, agent_key, run_key) do
        {:ok, normalized} -> {:cont, {:ok, [normalized | acc]}}
        error -> {:halt, error}
      end
    end)
    |> case do
      {:ok, normalized} -> {:ok, Enum.reverse(normalized)}
      error -> error
    end
  end

  defp normalize_events(_, _, _), do: {:error, :events_must_be_a_list}

  defp normalize_event(event, agent_key, run_key) when is_map(event) do
    with {:ok, activity} <- required_string(event, "activity"),
         {:ok, sequence} <- required_integer(event, "sequence"),
         {:ok, occurred_at} <- required_timestamp(event, "timestamp"),
         {:ok, standing} <- normalize_standing(Map.get(event, "standing", "UNKNOWN")) do
      event_key = Map.get(event, "id") || "#{run_key}:#{sequence}"
      lifecycle = Map.get(event, "lifecycle", "complete")
      authority_domain = Map.get(event, "authority_domain", "OBSERVE")
      now = DateTime.utc_now()
      payload = Map.get(event, "payload", %{})

      objects =
        event
        |> Map.get("objects", [])
        |> normalize_event_objects()

      {:ok,
       %{
         id: Ecto.UUID.bingenerate(),
         event_key: event_key,
         agent_key: agent_key,
         run_key: run_key,
         activity: activity,
         lifecycle: lifecycle,
         sequence: sequence,
         standing: standing,
         authority_domain: authority_domain,
         occurred_at: occurred_at,
         ingested_at: now,
         digest: Map.get(event, "digest") || digest(event),
         previous_digest: event["previous_digest"],
         payload: payload,
         objects: objects,
         inserted_at: now,
         updated_at: now
       }}
    end
  end

  defp normalize_event(_, _, _), do: {:error, :invalid_event}

  defp normalize_event_objects(objects) when is_list(objects) do
    Enum.flat_map(objects, fn
      %{"id" => id, "type" => type} = object when is_binary(id) and is_binary(type) ->
        [
          %{
            object_key: id,
            object_type: type,
            label: object["label"],
            qualifier: Map.get(object, "qualifier", "relatesTo"),
            attributes: Map.get(object, "attributes", %{})
          }
        ]

      _ ->
        []
    end)
  end

  defp normalize_event_objects(_), do: []

  defp normalize_objects(objects) when is_list(objects) do
    now = DateTime.utc_now()

    rows =
      Enum.flat_map(objects, fn
        %{"id" => id, "type" => type} = object when is_binary(id) and is_binary(type) ->
          [
            %{
              id: Ecto.UUID.bingenerate(),
              object_key: id,
              object_type: type,
              label: object["label"],
              attributes: Map.get(object, "attributes", %{}),
              first_seen_at: now,
              last_seen_at: now,
              inserted_at: now,
              updated_at: now
            }
          ]

        _ ->
          []
      end)

    {:ok, rows}
  end

  defp normalize_objects(_), do: {:error, :objects_must_be_a_list}

  defp merge_objects(objects, events) do
    now = DateTime.utc_now()

    event_objects =
      for event <- events,
          object <- event.objects do
        %{
          id: Ecto.UUID.bingenerate(),
          object_key: object.object_key,
          object_type: object.object_type,
          label: object.label,
          attributes: object.attributes,
          first_seen_at: now,
          last_seen_at: now,
          inserted_at: now,
          updated_at: now
        }
      end

    (objects ++ event_objects)
    |> Enum.uniq_by(& &1.object_key)
  end

  defp event_object_rows(events) do
    now = DateTime.utc_now()

    for event <- events,
        object <- event.objects do
      %{
        id: Ecto.UUID.bingenerate(),
        event_key: event.event_key,
        object_key: object.object_key,
        qualifier: object.qualifier,
        inserted_at: now,
        updated_at: now
      }
    end
  end

  defp normalize_object_relationships(rows) when is_list(rows) do
    now = DateTime.utc_now()

    normalized =
      Enum.flat_map(rows, fn
        %{"source" => source, "target" => target} = row
        when is_binary(source) and is_binary(target) ->
          [
            %{
              id: Ecto.UUID.bingenerate(),
              source_object_key: source,
              target_object_key: target,
              qualifier: Map.get(row, "qualifier", "relatesTo"),
              inserted_at: now,
              updated_at: now
            }
          ]

        _ ->
          []
      end)

    {:ok, normalized}
  end

  defp normalize_object_relationships(_), do: {:error, :object_relationships_must_be_a_list}

  defp normalize_receipts(rows, run_key) when is_list(rows) do
    now = DateTime.utc_now()

    {:ok,
     Enum.flat_map(rows, fn
       receipt when is_map(receipt) ->
         payload = Map.get(receipt, "payload", receipt)
         digest_value = Map.get(receipt, "digest") || digest(payload)

         [
           %{
             id: Ecto.UUID.bingenerate(),
             receipt_key: Map.get(receipt, "id") || digest_value,
             run_key: run_key,
             standing: Map.get(receipt, "standing", "UNKNOWN"),
             subject_sha: receipt["subject_sha"],
             subject_tree_sha: receipt["subject_tree_sha"],
             digest: digest_value,
             payload: payload,
             observed_at: parse_timestamp_or_now(receipt["timestamp"], now),
             inserted_at: now,
             updated_at: now
           }
         ]

       _ ->
         []
     end)}
  end

  defp normalize_receipts(_, _), do: {:error, :receipts_must_be_a_list}

  defp normalize_conformance(rows, run_key) when is_list(rows) do
    now = DateTime.utc_now()

    {:ok,
     Enum.flat_map(rows, fn
       row when is_map(row) ->
         payload = Map.get(row, "payload", row)
         key = Map.get(row, "id") || digest(payload)

         [
           %{
             id: Ecto.UUID.bingenerate(),
             result_key: key,
             run_key: run_key,
             model_key: row["model_key"],
             fitness: decimal_or_nil(row["fitness"]),
             standing: Map.get(row, "standing", "UNKNOWN"),
             payload: payload,
             observed_at: parse_timestamp_or_now(row["timestamp"], now),
             inserted_at: now,
             updated_at: now
           }
         ]

       _ ->
         []
     end)}
  end

  defp normalize_conformance(_, _), do: {:error, :conformance_results_must_be_a_list}

  defp normalize_refusals(rows, run_key) when is_list(rows) do
    now = DateTime.utc_now()

    {:ok,
     Enum.flat_map(rows, fn
       %{"type" => type} = row when is_binary(type) ->
         payload = Map.get(row, "payload", row)

         [
           %{
             id: Ecto.UUID.bingenerate(),
             refusal_key: Map.get(row, "id") || digest(payload),
             run_key: run_key,
             refusal_type: type,
             reason: row["reason"],
             payload: payload,
             observed_at: parse_timestamp_or_now(row["timestamp"], now),
             inserted_at: now,
             updated_at: now
           }
         ]

       _ ->
         []
     end)}
  end

  defp normalize_refusals(_, _), do: {:error, :refusals_must_be_a_list}

  defp normalize_variants(rows) when is_list(rows) do
    now = DateTime.utc_now()

    {:ok,
     Enum.flat_map(rows, fn
       %{"id" => id, "name" => name, "model_type" => model_type, "model_digest" => model_digest} =
           row
       when is_binary(id) and is_binary(name) and is_binary(model_type) and
              is_binary(model_digest) ->
         [
           %{
             id: Ecto.UUID.bingenerate(),
             variant_key: id,
             name: name,
             model_type: model_type,
             model_digest: model_digest,
             payload: Map.get(row, "payload", %{}),
             first_seen_at: now,
             last_seen_at: now,
             inserted_at: now,
             updated_at: now
           }
         ]

       _ ->
         []
     end)}
  end

  defp normalize_variants(_), do: {:error, :process_variants_must_be_a_list}

  defp broadcast([]), do: :ok

  defp broadcast(events) do
    Phoenix.PubSub.broadcast(
      ChatGPTCloud.PubSub,
      "process-intelligence:ocel",
      {:ocel_events, events}
    )
  end

  defp required_string(map, key) do
    case map[key] do
      value when is_binary(value) and byte_size(value) > 0 -> {:ok, value}
      _ -> {:error, {:missing_or_invalid, key}}
    end
  end

  defp required_integer(map, key) do
    case map[key] do
      value when is_integer(value) ->
        {:ok, value}

      value when is_binary(value) ->
        case Integer.parse(value) do
          {integer, ""} -> {:ok, integer}
          _ -> {:error, {:missing_or_invalid, key}}
        end

      _ ->
        {:error, {:missing_or_invalid, key}}
    end
  end

  defp required_timestamp(map, key) do
    case map[key] do
      value when is_binary(value) ->
        case DateTime.from_iso8601(value) do
          {:ok, datetime, _offset} -> {:ok, datetime}
          _ -> {:error, {:missing_or_invalid, key}}
        end

      %DateTime{} = datetime ->
        {:ok, datetime}

      _ ->
        {:error, {:missing_or_invalid, key}}
    end
  end

  defp normalize_standing("REFUSED_" <> _ = standing), do: {:ok, standing}
  defp normalize_standing(standing) when standing in @standings, do: {:ok, standing}
  defp normalize_standing(_), do: {:error, :invalid_standing}

  defp parse_timestamp_or_now(nil, now), do: now

  defp parse_timestamp_or_now(value, now) do
    parse_optional_timestamp(value) || now
  end

  defp parse_optional_timestamp(nil), do: nil
  defp parse_optional_timestamp(%DateTime{} = value), do: value

  defp parse_optional_timestamp(value) when is_binary(value) do
    case DateTime.from_iso8601(value) do
      {:ok, datetime, _offset} -> datetime
      _ -> nil
    end
  end

  defp parse_optional_timestamp(_), do: nil

  defp decimal_or_nil(nil), do: nil
  defp decimal_or_nil(%Decimal{} = value), do: value

  defp decimal_or_nil(value) when is_number(value) or is_binary(value) do
    Decimal.new(to_string(value))
  rescue
    _ -> nil
  end

  defp digest(term) do
    term
    |> Jason.encode!()
    |> then(&:crypto.hash(:sha256, &1))
    |> Base.encode16(case: :lower)
  end
end
