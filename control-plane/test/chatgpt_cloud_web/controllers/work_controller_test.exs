defmodule ChatGPTCloudWeb.WorkControllerTest do
  use ChatGPTCloudWeb.ConnCase, async: false

  test "requires the existing bearer-token control-plane boundary", %{conn: conn} do
    conn =
      post(conn, "/api/v1/swarm/work", %{
        "work_type" => "implementation",
        "description" => "must not be anonymous"
      })

    assert conn.status == 401
  end

  test "accepts and advances the SwarmSH JSON work protocol", %{conn: conn} do
    created =
      conn
      |> put_req_header("authorization", "Bearer test-token")
      |> post("/api/v1/swarm/work", %{
        "work_item_id" => "work_controller_lifecycle",
        "work_type" => "implementation",
        "description" => "exercise HTTP coordination",
        "priority" => "high"
      })
      |> json_response(202)

    assert created["work"]["schema"] == "swarmsh.work/v1"
    assert created["work"]["status"] == "pending"
    assert created["work"]["authority"]["do"]["granted"] == false

    claimed =
      build_conn()
      |> put_req_header("authorization", "Bearer test-token")
      |> post("/api/v1/swarm/work/work_controller_lifecycle/claim", %{
        "agent_id" => "chatgpt-agent-http"
      })
      |> json_response(200)

    assert claimed["work"]["status"] == "active"
    assert claimed["receipt"]["event_type"] == "claimed"

    progressed =
      build_conn()
      |> put_req_header("authorization", "Bearer test-token")
      |> post("/api/v1/swarm/work/work_controller_lifecycle/progress", %{
        "agent_id" => "chatgpt-agent-http",
        "progress" => 60
      })
      |> json_response(200)

    assert progressed["work"]["progress"] == 60
    assert progressed["work"]["status"] == "in_progress"

    completed =
      build_conn()
      |> put_req_header("authorization", "Bearer test-token")
      |> post("/api/v1/swarm/work/work_controller_lifecycle/complete", %{
        "agent_id" => "chatgpt-agent-http",
        "result" => %{"command" => "mix test", "exit" => 0}
      })
      |> json_response(200)

    assert completed["work"]["status"] == "completed"
    assert completed["receipt"]["standing"] == "PARTIAL_ALIVE"
  end
end
