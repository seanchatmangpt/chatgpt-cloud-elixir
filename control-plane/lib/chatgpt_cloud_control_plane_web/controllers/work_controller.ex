defmodule ChatGPTCloudWeb.WorkController do
  @moduledoc "Raw JSON control surface for SwarmSH-style work coordination."

  use ChatGPTCloudWeb, :controller

  alias ChatGPTCloud.SwarmCoordination.{Coordinator, Project2}

  def index(conn, params) do
    opts =
      []
      |> maybe_put(:status, params["status"])
      |> maybe_put(:limit, parse_limit(params["limit"]))

    with {:ok, work} <- Coordinator.list(opts) do
      json(conn, %{"schema" => "swarmsh.work-list/v1", "work" => work})
    end
  end

  def create(conn, params) do
    with {:ok, work, receipt} <- Coordinator.enqueue(params) do
      conn
      |> put_status(:accepted)
      |> json(%{"work" => work, "receipt" => receipt})
    else
      {:error, reason} -> render_error(conn, reason)
    end
  end

  def claim(conn, %{"work_item_id" => work_item_id} = params) do
    transition(conn, Coordinator.claim(work_item_id, params["agent_id"] || ""))
  end

  def progress(conn, %{"work_item_id" => work_item_id} = params) do
    transition(
      conn,
      Coordinator.progress(
        work_item_id,
        params["agent_id"] || "",
        params["progress"],
        params["status"] || "in_progress"
      )
    )
  end

  def complete(conn, %{"work_item_id" => work_item_id} = params) do
    transition(
      conn,
      Coordinator.complete(work_item_id, params["agent_id"] || "", params["result"] || %{})
    )
  end

  def block(conn, %{"work_item_id" => work_item_id} = params) do
    transition(
      conn,
      Coordinator.block(work_item_id, params["agent_id"] || "", params["reason"] || "")
    )
  end

  def refuse(conn, %{"work_item_id" => work_item_id} = params) do
    transition(
      conn,
      Coordinator.refuse(
        work_item_id,
        params["agent_id"] || "",
        params["refusal_type"] || "UNSPECIFIED",
        params["reason"] || ""
      )
    )
  end

  def import_project2(conn, params) do
    opts =
      []
      |> maybe_put(:max_items, parse_limit(params["max_items"]))
      |> maybe_put(:include_archived, params["include_archived"])

    case Project2.import(opts) do
      {:ok, receipt} ->
        conn
        |> put_status(:accepted)
        |> json(receipt)

      {:error, reason} ->
        render_error(conn, reason)
    end
  end

  defp transition(conn, {:ok, work, receipt}) do
    json(conn, %{"work" => work, "receipt" => receipt})
  end

  defp transition(conn, {:error, reason}), do: render_error(conn, reason)

  defp render_error(conn, %{"type" => type} = reason) do
    status =
      case type do
        "WORK_NOT_FOUND" -> :not_found
        "INVALID_PROGRESS" -> :unprocessable_entity
        _ -> :conflict
      end

    conn
    |> put_status(status)
    |> json(%{"error" => reason})
  end

  defp render_error(conn, reason) do
    conn
    |> put_status(:unprocessable_entity)
    |> json(%{"error" => inspect(reason)})
  end

  defp maybe_put(opts, _key, nil), do: opts
  defp maybe_put(opts, key, value), do: Keyword.put(opts, key, value)

  defp parse_limit(nil), do: nil
  defp parse_limit(value) when is_integer(value), do: value

  defp parse_limit(value) when is_binary(value) do
    case Integer.parse(value) do
      {parsed, ""} -> parsed
      _ -> nil
    end
  end
end
