defmodule ChatGPTCloudWeb.IngestController do
  use ChatGPTCloudWeb, :controller

  alias ChatGPTCloud.ProcessIntelligence.Ingestor

  def create(conn, params) do
    case Ingestor.ingest(params) do
      {:ok, result} ->
        conn
        |> put_status(:accepted)
        |> json(result)

      {:error, reason} ->
        conn
        |> put_status(:unprocessable_entity)
        |> json(%{standing: "BLOCKED", error: inspect(reason)})
    end
  end
end
