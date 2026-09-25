defmodule ChatGPTCloud.Xaas.FabricTest do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.Xaas.{Capabilities, Fabric, Receipt, Target}

  @req %{"goal" => "fabric pure test", "idempotency_key" => "pure-001"}
  @probe %{
    "protocol" => "xaas-fabric/1",
    "capabilities" => Capabilities.allowlist(),
    "long_poll_max_ms" => 25_000
  }
  @admit %{"admitted" => Capabilities.allowlist(), "refused" => []}
  @submitted %{"run_id" => "r1", "epoch_id" => "e1", "replay" => false}
  @sealed %{"epoch_id" => "e1", "outcome" => "alive"}

  defp to_submitted do
    Fabric.new(@req, wait_ms: 100)
    |> Fabric.apply({:ok, 200, @probe})
    |> Fabric.apply({:ok, 200, @admit})
    |> Fabric.apply({:ok, 201, @submitted})
  end

  test "legal sequence probe -> admit -> submit -> leased -> sealed -> replayed" do
    s = Fabric.new(@req, wait_ms: 100)
    assert Fabric.next(s) == {:request, :get, "/internal-api/fabric/probe", nil}
    s = Fabric.apply(s, {:ok, 200, @probe})
    assert s.phase == :probed

    assert Fabric.next(s) ==
             {:request, :post, "/internal-api/fabric/admit",
              %{"capabilities" => Capabilities.allowlist()}}

    s = Fabric.apply(s, {:ok, 200, @admit})

    assert {:request, :post, "/internal-api/fabric/runs",
            %{"idempotency_key" => "pure-001", "provider" => "zcode"}} =
             Fabric.next(s)

    s = Fabric.apply(s, {:ok, 201, @submitted})
    assert {s.phase, s.epoch_id} == {:submitted, "e1"}

    assert Fabric.next(s) ==
             {:request, :get, "/internal-api/fabric/epochs/e1/receipts?wait_ms=100", nil}

    s = Fabric.apply(s, {:ok, 204, nil})
    assert {s.phase, s.polls} == {:submitted, 1}
    s = Fabric.apply(s, {:ok, 200, %{"state" => "leased", "receipts" => []}})
    assert s.phase == :leased

    d = Receipt.digest(@sealed)

    s =
      Fabric.apply(
        s,
        {:ok, 200, %{"receipts" => [%{"receipt" => @sealed, "digest" => d}], "cursor" => d}}
      )

    assert Fabric.next(s) == {:replay, @sealed, d}
    s = Fabric.apply(s, :replay)
    assert s.phase == :replayed
    assert Fabric.next(s) == {:done, @sealed}
    assert Fabric.receipt(s)["standing"] == "ALIVE"
    assert Fabric.receipt(s)["identity"]["sealed_receipt_sha256"] == d
  end

  test "long-poll cursor is carried after a seal digest is seen" do
    s = %{to_submitted() | cursor: "abc"}

    assert Fabric.next(s) ==
             {:request, :get, "/internal-api/fabric/epochs/e1/receipts?wait_ms=100&after=abc",
              nil}
  end

  test "tampered seal digest is REFUSED(replay_digest_mismatch)" do
    s =
      to_submitted()
      |> Fabric.apply(
        {:ok, 200,
         %{"receipts" => [%{"receipt" => @sealed, "digest" => String.duplicate("0", 64)}]}}
      )
      |> Fabric.apply(:replay)

    assert s.phase == {:refused, "replay_digest_mismatch"}
    assert Fabric.receipt(s)["standing"] == "REFUSED"
  end

  test "probe advertising actuate or missing a capability is UNSUPPORTED(CONTRACT_MISMATCH)" do
    for caps <- [["fabric.probe", "run.submit", "epoch.receipts", "actuate"], ["fabric.probe"]] do
      s = Fabric.new(@req) |> Fabric.apply({:ok, 200, %{@probe | "capabilities" => caps}})
      assert s.phase == {:unsupported, "CONTRACT_MISMATCH"}
    end
  end

  test "partial admission is REFUSED(CAPABILITY_NOT_ADMITTED)" do
    s =
      Fabric.new(@req)
      |> Fabric.apply({:ok, 200, @probe})
      |> Fabric.apply({:ok, 200, %{"admitted" => ["fabric.probe"], "refused" => []}})

    assert s.phase == {:refused, "CAPABILITY_NOT_ADMITTED"}
  end

  test "terminal states are absorbing and never emit a request" do
    s = Fabric.new(@req) |> Fabric.apply({:ok, 401, %{}})
    assert Fabric.next(s) == {:refused, "AUTHENTICATION"}
    assert Fabric.terminal?(s)
  end

  test "invalid requests are refused before any request" do
    assert Fabric.new(%{"goal" => "", "idempotency_key" => "k"}).phase ==
             {:refused, "GOAL_REQUIRED"}

    assert Fabric.new(%{"goal" => "g", "idempotency_key" => "bad key/"}).phase ==
             {:refused, "IDEMPOTENCY_KEY_INVALID"}
  end

  test "resume with a journalled epoch refuses a different epoch (IDEMPOTENCY_VIOLATION)" do
    journal = Fabric.journal(to_submitted())

    s =
      Fabric.resume(journal)
      |> Fabric.apply({:ok, 200, @probe})
      |> Fabric.apply({:ok, 200, @admit})
      |> Fabric.apply({:ok, 200, %{@submitted | "epoch_id" => "e2", "replay" => true}})

    assert s.phase == {:refused, "IDEMPOTENCY_VIOLATION"}

    ok =
      Fabric.resume(journal)
      |> Fabric.apply({:ok, 200, @probe})
      |> Fabric.apply({:ok, 200, @admit})
      |> Fabric.apply({:ok, 200, %{@submitted | "replay" => true}})

    assert {ok.phase, ok.epoch_id, ok.replay?, ok.resumed?} == {:submitted, "e1", true, true}
  end

  test "classify/2 mirrors Python classify_http" do
    table = [
      {200, nil, {"ALIVE", nil}},
      {204, nil, {"ALIVE", nil}},
      {401, nil, {"REFUSED_AUTHENTICATION", "AUTHENTICATION"}},
      {403, nil, {"REFUSED_AUTHORITY", "AUTHORITY"}},
      {404, nil, {"BLOCKED", "NOT_FOUND_OR_NOT_VISIBLE"}},
      {422, nil, {"REFUSED_REQUEST", "HTTP_422"}},
      {429, nil, {"BLOCKED", "CAPACITY"}},
      {500, nil, {"BLOCKED", "HTTP_500"}},
      {503, nil, {"BLOCKED", "SERVER_MISCONFIGURED"}},
      {0, {:error, {:network, :timeout}}, {"BLOCKED", "NETWORK"}},
      {0, {:error, {:config, :url_userinfo_refused}},
       {"BLOCKED", "IRREDUCIBLE_TRANSPORT_CONFIG"}},
      {0, {:error, {:redirect, 302}}, {"BLOCKED", "REDIRECT_REFUSED"}},
      {0, {:error, {:protocol, :bad}}, {"BUILD_BROKEN", "PROTOCOL"}}
    ]

    for {status, err, expected} <- table, do: assert(Fabric.classify(status, err) == expected)
  end

  test "capabilities: three admitted, actuate refused by authority ceiling, unknown fails closed" do
    assert Capabilities.allowlist() == ~w(fabric.probe run.submit epoch.receipts)
    for v <- Capabilities.allowlist(), do: assert(Capabilities.admit(v) == :ok)
    assert Capabilities.admit("actuate") == {:refused, {:authority_ceiling, "actuate"}}

    assert Capabilities.admit("claim_next") ==
             {:refused, {:capability_not_admitted, "claim_next"}}
  end

  test "target base_url matches Python Target.base_url" do
    t =
      Target.resolve(%{
        "XAAS_MCP_URL" => "https://h.example:8443/pfx/internal-api/execution/mcp/"
      })

    assert Target.base_url(t) == {:ok, "https://h.example:8443/pfx"}

    assert Target.base_url(Target.resolve(%{"XAAS_MCP_URL" => "https://h/other"})) ==
             {:error, {:config, :mcp_url_suffix}}

    assert Target.resolve(%{"XAAS_MCP_TOKEN" => "t"}).authorization == "Bearer t"
    assert Target.missing_config(%{}) == ["XAAS_MCP_URL", "XAAS_MCP_TOKEN"]
  end
end
