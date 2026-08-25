defmodule ChatGPTCloudWeb.HealthController do
  use ChatGPTCloudWeb, :controller

  def show(conn, _params) do
    case Ecto.Adapters.SQL.query(ChatGPTCloud.Repo, "SELECT 1", []) do
      {:ok, _} ->
        json(conn, %{status: "ok", standing: "ALIVE"})

      {:error, _} ->
        conn |> put_status(503) |> json(%{status: "database_unavailable", standing: "BLOCKED"})
    end
  end
end
