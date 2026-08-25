defmodule ChatGPTCloudWeb.OcelAuth do
  @moduledoc false
  import Plug.Conn

  def init(opts), do: opts

  def call(conn, _opts) do
    expected = Application.fetch_env!(:chatgpt_cloud_control_plane, :ocel_ingest_token)

    with ["Bearer " <> supplied] <- get_req_header(conn, "authorization"),
         true <- secure_equal?(supplied, expected) do
      conn
    else
      _ ->
        conn
        |> put_resp_content_type("application/json")
        |> send_resp(401, Jason.encode!(%{error: "unauthorized"}))
        |> halt()
    end
  end

  defp secure_equal?(left, right)
       when is_binary(left) and is_binary(right) and byte_size(left) == byte_size(right),
       do: Plug.Crypto.secure_compare(left, right)

  defp secure_equal?(_, _), do: false
end
