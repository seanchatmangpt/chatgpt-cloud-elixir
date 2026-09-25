defmodule ChatGPTCloud.Xaas.FabricHttpTest do
  @moduledoc """
  Client against a CONTRACT FIXTURE SERVER (`test/support/contract_server.ex`): a real
  Bandit listener on loopback, real sockets, real `:httpc`. No owned code is replaced.
  The live XaaS leg (P4 B4) remains the true contract test.
  """
  use ExUnit.Case, async: true

  alias ChatGPTCloud.Xaas.{Runner, Target}
  alias ChatGPTCloud.Xaas.Test.{Catcher, ContractServer}
  alias ChatGPTCloud.Xaas.Transport.Http

  @moduletag :tmp_dir

  defp server(config \\ %{}), do: ContractServer.start(&start_supervised!/1, config)

  defp target(srv, token \\ nil),
    do: Target.resolve(%{"XAAS_MCP_URL" => srv.mcp_url, "XAAS_MCP_TOKEN" => token || srv.token})

  defp opts(ctx, extra \\ []),
    do:
      Keyword.merge([journal_dir: ctx.tmp_dir, timeout: 2_000, wait_ms: 50, max_steps: 12], extra)

  defp req(key), do: %{"goal" => "fixture goal #{key}", "idempotency_key" => key}

  test "full sequence reaches ALIVE with a replay-verified sealed receipt", ctx do
    srv = server(%{polls: [:timeout, :leased, :sealed]})
    {state, receipt} = Runner.run(Http, target(srv), req("full-001"), opts(ctx))

    assert state.phase == :replayed
    assert receipt["standing"] == "ALIVE"
    assert receipt["authority"] == "CONSTRUCT"
    assert receipt["authenticated"] == true
    assert receipt["endpoint"] == "http://<redacted-host>/internal-api/execution/mcp"
    refute receipt |> ChatGPTCloud.Xaas.Receipt.canonical() |> String.contains?(srv.token)

    assert Enum.map(receipt["consequence"]["trace"], & &1["step"]) ==
             ~w(probe admit submit receipts receipts receipts replay)

    assert Enum.map(receipt["consequence"]["trace"], & &1["reason"]) ==
             [nil, nil, nil, "LONG_POLL_TIMEOUT", "LEASED", "SEALED", nil]

    run = ContractServer.runs(srv)["full-001"]
    assert receipt["identity"]["epoch_id"] == run.epoch_id
    assert receipt["sealed_receipt"] == ContractServer.sealed_receipt(run)
    # the receipt digests every other field
    body = Map.delete(receipt, "receipt_sha256")
    assert receipt["receipt_sha256"] == ChatGPTCloud.Xaas.Receipt.digest(body)
  end

  test "302 is refused and the bearer never reaches the redirect host", ctx do
    catcher = Catcher.start(&start_supervised!/1)
    srv = server(%{redirect_to: catcher.url})
    {state, receipt} = Runner.run(Http, target(srv), req("redir-001"), opts(ctx))

    assert state.phase == {:blocked, "REDIRECT_REFUSED"}
    assert receipt["standing"] == "BLOCKED"
    assert Catcher.seen(catcher) == []
    assert [{"GET", "/internal-api/fabric/probe", "Bearer " <> _}] = ContractServer.log(srv)
  end

  test "401, 403 and 503 each get their typed standing", ctx do
    srv = server()
    {s401, r401} = Runner.run(Http, target(srv, "wrong-token"), req("auth-001"), opts(ctx))

    assert {s401.phase, r401["standing"]} ==
             {{:refused, "AUTHENTICATION"}, "REFUSED_AUTHENTICATION"}

    for {code, phase, standing} <- [
          {403, {:refused, "fixture_override"}, "REFUSED_AUTHORITY"},
          {503, {:blocked, "SERVER_MISCONFIGURED"}, "BLOCKED"}
        ] do
      srv = server(%{status_override: code})
      {s, r} = Runner.run(Http, target(srv), req("status-#{code}"), opts(ctx))
      assert {s.phase, r["standing"]} == {phase, standing}
    end
  end

  test "timeout is BLOCKED(NETWORK)", ctx do
    srv = server(%{slow_ms: 1_000})
    {state, receipt} = Runner.run(Http, target(srv), req("slow-001"), opts(ctx, timeout: 200))
    assert state.phase == {:blocked, "NETWORK"}
    assert receipt["reason"] == "NETWORK"
  end

  test "long-poll: 204 on timeout, then 200 sealed", ctx do
    srv = server(%{polls: [:timeout, :timeout, :sealed]})
    {state, _receipt} = Runner.run(Http, target(srv), req("poll-001"), opts(ctx))
    assert state.phase == :replayed

    statuses =
      state.trace
      |> Enum.reverse()
      |> Enum.filter(&(&1["step"] == "receipts"))
      |> Enum.map(& &1["http_status"])

    assert statuses == [204, 204, 200]

    assert [_, _, _, {"GET", "/internal-api/fabric/epochs/" <> _, _} | _] =
             ContractServer.log(srv)
  end

  test "step budget exhausted while awaiting seal is PARTIAL_ALIVE(AWAITING_SEAL)", ctx do
    srv = server(%{polls: [:timeout]})
    {state, receipt} = Runner.run(Http, target(srv), req("budget-001"), opts(ctx, max_steps: 5))
    assert state.phase == :submitted
    assert {receipt["standing"], receipt["reason"]} == {"PARTIAL_ALIVE", "AWAITING_SEAL"}
  end

  test "actuate is 403 REFUSED(authority_ceiling:actuate)" do
    srv = server()
    t = target(srv)

    assert Http.request(:post, "/internal-api/fabric/actuate", %{}, target: t) ==
             {:ok, 403, %{"standing" => "REFUSED", "reason" => "authority_ceiling:actuate"}}

    assert ChatGPTCloud.Xaas.Fabric.classify(403, nil) == {"REFUSED_AUTHORITY", "AUTHORITY"}
  end

  test "tampered replay digest is REFUSED(replay_digest_mismatch)", ctx do
    srv = server(%{tamper: true})
    {state, receipt} = Runner.run(Http, target(srv), req("tamper-001"), opts(ctx))
    assert state.phase == {:refused, "replay_digest_mismatch"}
    assert {receipt["standing"], receipt["reason"]} == {"REFUSED", "replay_digest_mismatch"}
  end

  test "crash after submit, then resume with the same key returns the same epoch_id", ctx do
    srv = server(%{drop_first_submit_ms: 800})
    {crashed, _} = Runner.run(Http, target(srv), req("crash-001"), opts(ctx, timeout: 300))

    # The server recorded the run; the client never saw the response.
    assert crashed.phase == {:blocked, "NETWORK"}
    assert crashed.epoch_id == nil
    recorded = ContractServer.runs(srv)["crash-001"]
    assert recorded

    journal = ctx.tmp_dir |> Path.join("crash-001.json") |> File.read!() |> JSON.decode!()
    assert journal["request"]["idempotency_key"] == "crash-001"
    assert journal["epoch_id"] == nil

    Process.sleep(600)
    {resumed, receipt} = Runner.resume(Http, target(srv), "crash-001", opts(ctx))
    assert resumed.phase == :replayed
    assert resumed.resumed? and resumed.replay?
    assert resumed.epoch_id == recorded.epoch_id
    assert receipt["consequence"]["idempotent_replay"] == true
    assert map_size(ContractServer.runs(srv)) == 1
  end

  test "resume without a journal is refused", ctx do
    srv = server()
    assert Runner.resume(Http, target(srv), "missing-001", opts(ctx)) == {:error, :no_journal}
  end

  test "URL userinfo and non-http schemes are refused before any socket opens" do
    t = %Target{
      mcp_url: "http://u:p@127.0.0.1:1/internal-api/execution/mcp",
      authorization: "Bearer x"
    }

    assert Http.request(:get, "/internal-api/fabric/probe", nil, target: t) ==
             {:error, {:config, :url_userinfo_refused}}

    t = %Target{mcp_url: "ftp://127.0.0.1/internal-api/execution/mcp", authorization: nil}

    assert Http.request(:get, "/internal-api/fabric/probe", nil, target: t) ==
             {:error, {:config, :url_invalid}}
  end
end
