defmodule ChatGPTCloud.SwarmCoordination.Coordinator do
  @moduledoc """
  SwarmSH-style JSON work coordination over PostgreSQL.

  JSON is the portable control envelope. PostgreSQL row locks arbitrate claims.
  Model/planner/request data never acquires ambient DO authority: every work
  item is projected with `authority.do.granted = false` and `requires = BRCE`.
  """

  import Ecto.Query

  alias ChatGPTCloud.Repo
  alias ChatGPTCloud.SwarmCoordination.{Receipt, WorkItem}

  @claimable_status "pending"
  @owned_statuses ["active", "in_progress"]
  @terminal_statuses ["completed", "blocked", "refused"]

  def enqueue(attrs) when is_map(attrs) do
    now = now()
    work_item_id = value(attrs, :work_item_id) || "work_#{Ecto.UUID.generate()}"

    case Repo.get_by(WorkItem, work_item_id: work_item_id) do
      nil ->
        trace_id = nested_value(attrs, :telemetry, :trace_id) || trace_id()

        work = %WorkItem{
          work_item_id: work_item_id,
          source_kind: value(attrs, :source_kind),
          source_id: value(attrs, :source_id),
          work_type: value(attrs, :work_type, "general"),
          description: value(attrs, :description, ""),
          priority: value(attrs, :priority, "medium"),
          team: value(attrs, :team, "chatgpt_swarm"),
          status: "pending",
          reactor_id: value(attrs, :reactor_id, "chatgpt_cloud"),
          estimated_duration: value(attrs, :estimated_duration, "30m"),
          progress: 0,
          subject: json_map(value(attrs, :subject, %{})),
          authority: authority_fence(),
          telemetry: %{
            "trace_id" => trace_id,
            "span_id" => span_id(),
            "operation" => "swarm.work.enqueue",
            "service" => "chatgpt-cloud-elixir"
          },
          metadata: json_map(value(attrs, :metadata, %{})),
          result: %{},
          last_update: now
        }

        case Repo.insert(work) do
          {:ok, inserted} ->
            receipt = insert_receipt!(inserted, "enqueued", nil, "PARTIAL_ALIVE", %{})
            emit(:enqueued, inserted, receipt)
            {:ok, envelope(inserted), receipt_envelope(receipt)}

          {:error, error} ->
            {:error, error}
        end

      existing ->
        receipt =
          insert_receipt!(existing, "enqueue_replayed", existing.agent_id, "PARTIAL_ALIVE", %{})

        emit(:enqueue_replayed, existing, receipt)
        {:ok, envelope(existing), receipt_envelope(receipt)}
    end
  end

  def get(work_item_id) do
    case Repo.get_by(WorkItem, work_item_id: work_item_id) do
      nil -> {:error, error("UNKNOWN", "WORK_NOT_FOUND", work_item_id)}
      work -> {:ok, envelope(work)}
    end
  end

  def list(opts \\ []) do
    limit = opts |> Keyword.get(:limit, 100) |> min(500) |> max(1)
    status = Keyword.get(opts, :status)

    query =
      from w in WorkItem,
        order_by: [desc: w.inserted_at],
        limit: ^limit

    query = if status, do: from(w in query, where: w.status == ^status), else: query
    {:ok, Enum.map(Repo.all(query), &envelope/1)}
  end

  def claim(work_item_id, agent_id) when is_binary(agent_id) and agent_id != "" do
    transact(work_item_id, fn work ->
      cond do
        work.status == @claimable_status ->
          updated =
            update!(work,
              status: "active",
              agent_id: agent_id,
              claimed_at: now(),
              last_update: now(),
              telemetry: telemetry(work, "swarm.work.claim")
            )

          receipt = insert_receipt!(updated, "claimed", agent_id, "PARTIAL_ALIVE", %{})
          emit(:claimed, updated, receipt)
          {updated, receipt}

        work.status in @owned_statuses and work.agent_id == agent_id ->
          receipt = insert_receipt!(work, "claim_replayed", agent_id, "PARTIAL_ALIVE", %{})
          emit(:claim_replayed, work, receipt)
          {work, receipt}

        work.status in @owned_statuses ->
          Repo.rollback(
            error("REFUSED", "CLAIM_CONFLICT", work_item_id, %{
              "claimed_by" => work.agent_id,
              "requested_by" => agent_id
            })
          )

        true ->
          Repo.rollback(invalid_transition(work, "claim"))
      end
    end)
  end

  def claim(work_item_id, agent_id) do
    {:error,
     error("REFUSED", "INVALID_AGENT_ID", work_item_id, %{
       "agent_id" => agent_id,
       "required" => "non-empty string"
     })}
  end

  def progress(work_item_id, agent_id, percent, status \\ "in_progress")

  def progress(work_item_id, agent_id, percent, status)
      when is_integer(percent) and percent >= 0 and percent <= 100 do
    transact(work_item_id, fn work ->
      require_owner!(work, agent_id, "progress")

      unless work.status in @owned_statuses do
        Repo.rollback(invalid_transition(work, "progress"))
      end

      updated =
        update!(work,
          status: normalize_progress_status(status),
          progress: percent,
          last_update: now(),
          telemetry: telemetry(work, "swarm.work.progress")
        )

      receipt =
        insert_receipt!(updated, "progress", agent_id, "PARTIAL_ALIVE", %{
          "progress" => percent,
          "status" => updated.status
        })

      emit(:progress, updated, receipt)
      {updated, receipt}
    end)
  end

  def progress(work_item_id, _agent_id, percent, _status) do
    {:error,
     error("REFUSED", "INVALID_PROGRESS", work_item_id, %{
       "progress" => percent,
       "required" => "integer 0..100"
     })}
  end

  def complete(work_item_id, agent_id, result \\ %{}) do
    transact(work_item_id, fn work ->
      require_owner!(work, agent_id, "complete")

      unless work.status in @owned_statuses do
        Repo.rollback(invalid_transition(work, "complete"))
      end

      result = normalize_result(result)
      standing = Map.get(result, "standing", "PARTIAL_ALIVE")

      updated =
        update!(work,
          status: "completed",
          progress: 100,
          result: result,
          completed_at: now(),
          last_update: now(),
          telemetry: telemetry(work, "swarm.work.complete")
        )

      receipt = insert_receipt!(updated, "completed", agent_id, standing, %{"result" => result})
      emit(:completed, updated, receipt)
      {updated, receipt}
    end)
  end

  def block(work_item_id, agent_id, reason) when is_binary(reason) and reason != "" do
    terminate(work_item_id, agent_id, "blocked", "BLOCKED", %{"reason" => reason})
  end

  def block(work_item_id, _agent_id, reason) do
    {:error,
     error("REFUSED", "INVALID_BLOCK_REASON", work_item_id, %{
       "reason" => reason,
       "required" => "non-empty string"
     })}
  end

  def refuse(work_item_id, agent_id, refusal_type, reason)
      when is_binary(refusal_type) and refusal_type != "" do
    terminate(work_item_id, agent_id, "refused", "REFUSED", %{
      "refusal_type" => refusal_type,
      "reason" => reason || ""
    })
  end

  def refuse(work_item_id, _agent_id, refusal_type, reason) do
    {:error,
     error("REFUSED", "INVALID_REFUSAL_TYPE", work_item_id, %{
       "refusal_type" => refusal_type,
       "reason" => reason,
       "required" => "non-empty string"
     })}
  end

  defp terminate(work_item_id, agent_id, terminal_status, standing, details) do
    transact(work_item_id, fn work ->
      require_owner!(work, agent_id, terminal_status)

      unless work.status in @owned_statuses do
        Repo.rollback(invalid_transition(work, terminal_status))
      end

      updated =
        update!(work,
          status: terminal_status,
          result: details,
          completed_at: now(),
          last_update: now(),
          telemetry: telemetry(work, "swarm.work.#{terminal_status}")
        )

      receipt = insert_receipt!(updated, terminal_status, agent_id, standing, details)
      emit(String.to_atom(terminal_status), updated, receipt)
      {updated, receipt}
    end)
  end

  defp transact(work_item_id, fun) do
    result =
      Repo.transaction(fn ->
        query =
          from w in WorkItem,
            where: w.work_item_id == ^work_item_id,
            lock: "FOR UPDATE"

        case Repo.one(query) do
          nil -> Repo.rollback(error("UNKNOWN", "WORK_NOT_FOUND", work_item_id))
          work -> fun.(work)
        end
      end)

    case result do
      {:ok, {work, receipt}} -> {:ok, envelope(work), receipt_envelope(receipt)}
      {:error, reason} -> {:error, reason}
    end
  end

  defp require_owner!(work, agent_id, operation) do
    if work.agent_id != agent_id do
      Repo.rollback(
        error("REFUSED", "NOT_CLAIM_OWNER", work.work_item_id, %{
          "operation" => operation,
          "claimed_by" => work.agent_id,
          "requested_by" => agent_id
        })
      )
    end
  end

  defp invalid_transition(work, operation) do
    error("REFUSED", "INVALID_TRANSITION", work.work_item_id, %{
      "operation" => operation,
      "status" => work.status,
      "terminal" => work.status in @terminal_statuses
    })
  end

  defp update!(work, fields) do
    work
    |> Ecto.Changeset.change(fields)
    |> Repo.update!()
  end

  defp insert_receipt!(work, event_type, agent_id, standing, details) do
    occurred_at = now()

    payload = %{
      "event" => event_type,
      "work" => envelope(work),
      "details" => json_map(details)
    }

    digest =
      payload
      |> Jason.encode!()
      |> then(&:crypto.hash(:sha256, &1))
      |> Base.encode16(case: :lower)

    %Receipt{
      receipt_id: "receipt_#{Ecto.UUID.generate()}",
      work_item_id: work.work_item_id,
      event_type: event_type,
      agent_id: agent_id,
      trace_id: get_in(work.telemetry || %{}, ["trace_id"]),
      standing: standing,
      digest: digest,
      payload: payload,
      occurred_at: occurred_at
    }
    |> Repo.insert!()
  end

  def envelope(work) do
    %{
      "schema" => "swarmsh.work/v1",
      "work_item_id" => work.work_item_id,
      "agent_id" => work.agent_id,
      "reactor_id" => work.reactor_id,
      "source" => %{"kind" => work.source_kind, "id" => work.source_id},
      "work_type" => work.work_type,
      "description" => work.description,
      "priority" => work.priority,
      "team" => work.team,
      "status" => work.status,
      "estimated_duration" => work.estimated_duration,
      "progress" => work.progress,
      "subject" => work.subject || %{},
      "authority" => work.authority || %{},
      "telemetry" => work.telemetry || %{},
      "metadata" => work.metadata || %{},
      "result" => work.result || %{},
      "claimed_at" => iso8601(work.claimed_at),
      "last_update" => iso8601(work.last_update),
      "completed_at" => iso8601(work.completed_at),
      "created_at" => iso8601(work.inserted_at),
      "updated_at" => iso8601(work.updated_at)
    }
  end

  def receipt_envelope(receipt) do
    %{
      "schema" => "swarmsh.receipt/v1",
      "receipt_id" => receipt.receipt_id,
      "work_item_id" => receipt.work_item_id,
      "event_type" => receipt.event_type,
      "agent_id" => receipt.agent_id,
      "trace_id" => receipt.trace_id,
      "standing" => receipt.standing,
      "digest" => receipt.digest,
      "occurred_at" => iso8601(receipt.occurred_at),
      "payload" => receipt.payload || %{}
    }
  end

  defp telemetry(work, operation) do
    (work.telemetry || %{})
    |> Map.put("operation", operation)
    |> Map.put("span_id", span_id())
  end

  defp emit(event, work, receipt) do
    :telemetry.execute(
      [:chatgpt_cloud, :swarm, :work, event],
      %{count: 1},
      %{
        work_item_id: work.work_item_id,
        agent_id: work.agent_id,
        status: work.status,
        trace_id: receipt.trace_id,
        receipt_id: receipt.receipt_id
      }
    )
  end

  defp authority_fence do
    %{
      "select" => %{"granted" => true},
      "construct" => %{"granted" => true},
      "do" => %{"granted" => false, "requires" => "BRCE"}
    }
  end

  defp normalize_progress_status("active"), do: "active"
  defp normalize_progress_status(_), do: "in_progress"

  defp normalize_result(result) when is_map(result), do: json_map(result)
  defp normalize_result(result), do: %{"result" => to_string(result)}

  defp error(standing, type, work_item_id, details \\ %{}) do
    %{
      "standing" => standing,
      "type" => type,
      "work_item_id" => work_item_id,
      "details" => details
    }
  end

  defp value(map, key, default \\ nil) do
    Map.get(map, key, Map.get(map, Atom.to_string(key), default))
  end

  defp nested_value(map, outer, inner) do
    case value(map, outer) do
      value when is_map(value) -> Map.get(value, inner, Map.get(value, Atom.to_string(inner)))
      _ -> nil
    end
  end

  defp json_map(value) when is_map(value) do
    value |> Jason.encode!() |> Jason.decode!()
  end

  defp json_map(_), do: %{}

  defp trace_id, do: random_hex(16)
  defp span_id, do: random_hex(8)
  defp random_hex(bytes), do: bytes |> :crypto.strong_rand_bytes() |> Base.encode16(case: :lower)
  defp now, do: DateTime.utc_now() |> DateTime.truncate(:microsecond)
  defp iso8601(nil), do: nil
  defp iso8601(%DateTime{} = value), do: DateTime.to_iso8601(value)
end
