defmodule Mix.Tasks.XaasRuntime.FabricTest do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.Xaas.Test.ContractServer
  alias Mix.Tasks.XaasRuntime.Fabric, as: Task

  @moduletag :tmp_dir

  test "missing config is BLOCKED(IRREDUCIBLE_TRANSPORT_CONFIG), never a localhost fallback",
       ctx do
    receipt = Task.execute([goal: "g", idempotency_key: "k1", journal_dir: ctx.tmp_dir], %{})
    assert {receipt["standing"], receipt["reason"]} == {"BLOCKED", "IRREDUCIBLE_TRANSPORT_CONFIG"}
    assert receipt["detail"] == "missing environment: XAAS_MCP_URL,XAAS_MCP_TOKEN"
    assert Task.exit_code(receipt["standing"]) == 69
  end

  test "execute against the contract fixture server yields ALIVE and exit code 0", ctx do
    srv = ContractServer.start(&start_supervised!/1)
    env = %{"XAAS_MCP_URL" => srv.mcp_url, "XAAS_MCP_TOKEN" => srv.token}

    receipt =
      Task.execute(
        [
          goal: "task goal",
          idempotency_key: "task-001",
          journal_dir: ctx.tmp_dir,
          wait_ms: 50,
          timeout_ms: 2_000
        ],
        env
      )

    assert receipt["standing"] == "ALIVE"
    assert Task.exit_code(receipt["standing"]) == 0
    assert Task.exit_code("REFUSED_AUTHORITY") == 77
  end
end
