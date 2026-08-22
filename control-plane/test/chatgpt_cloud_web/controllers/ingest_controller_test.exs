defmodule ChatGPTCloudWeb.IngestControllerTest do
  use ChatGPTCloudWeb.ConnCase, async: false

  test "requires the producer bearer token", %{conn: conn} do
    conn =
      post(conn, "/api/v1/ocel/batches", %{
        "schema" => "chatgpt-cloud-ocel/1",
        "producer" => %{"agent_id" => "agent", "run_id" => "run"},
        "events" => []
      })

    assert conn.status == 401
  end

  test "accepts a valid authenticated batch", %{conn: conn} do
    conn =
      conn
      |> put_req_header("authorization", "Bearer test-token")
      |> post("/api/v1/ocel/batches", %{
        "schema" => "chatgpt-cloud-ocel/1",
        "producer" => %{"agent_id" => "agent", "run_id" => "run"},
        "events" => [
          %{
            "id" => "controller-event-1",
            "activity" => "test.completed",
            "sequence" => 1,
            "standing" => "ALIVE",
            "timestamp" => "2026-08-22T00:00:00Z"
          }
        ]
      })

    assert %{"accepted_events" => 1, "standing" => "ALIVE"} = json_response(conn, 202)
  end
end
