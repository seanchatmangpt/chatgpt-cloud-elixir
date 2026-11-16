defmodule ChatGPTCloudWeb.FleetController do
  use ChatGPTCloudWeb, :controller

  alias ChatGPTCloud.ProcessIntelligence.Queries

  def index(conn, params) do
    opts =
      case parse_window(params) do
        {:ok, window} -> [window_seconds: window]
        :error -> []
      end

    conn
    |> put_status(:ok)
    |> json(Queries.fleet_snapshot(opts))
  end

  defp parse_window(%{"window_seconds" => raw}) do
    case Integer.parse(raw) do
      {n, ""} when n > 0 -> {:ok, n}
      _ -> :error
    end
  end

  defp parse_window(_), do: :error
end
