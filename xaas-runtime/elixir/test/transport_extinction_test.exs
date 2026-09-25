defmodule ChatGPTCloud.Xaas.TransportExtinctionTest do
  @moduledoc """
  ALOOP-ZCODE-DOGFOOD-001 LANE 4 -- TRANSPORT-EXTINCTION-001 court.

  Proves the environment and the transport are replaceable projections of the same
  execution semantics: ONE pure `ChatGPTCloud.Xaas.Fabric` state machine driven
  over TWO transport paths that speak the SAME `xaas-fabric/1` protocol --

    * PATH A: `ChatGPTCloud.Xaas.Transport.Http` -- real `:httpc` over TCP loopback;
    * PATH B: `ChatGPTCloud.Xaas.Test.InProcTransport` -- in-process Plug dispatch,
      no socket,

  both against ONE execution substrate (the `ChatGPTCloud.Xaas.Test.ContractServer`
  agent, standing in for the XaaS epoch store), so work-order identity, idempotency
  and receipt identity are shared across paths. Provider identity is always
  `"zcode"` inside the request; the transport identity is which module the runner
  is given -- the two never mix.

  Fault matrix (every scenario carries its id + seed in the idempotency key):

    TE-001  transport unavailable at start          -> typed BLOCKED(NETWORK), bounded
    TE-002  mid-flight drop (submit ACK lost)       -> BLOCKED(NETWORK), run recorded
    TE-003  restart on the OTHER transport          -> replay: true, same epoch
    TE-100  TRANSPORT-EXTINCTION-001 court          -> path A killed between submit
               and receipt; execution continues on path B; same work-order identity,
               same normalized receipt schema; duplicate after reconnect replays
    TE-101  anti-vacuity: broken seal on path B     -> court CAN fail (REFUSED);
               schema comparator CAN fail
    TE-102  duplicate submission across paths       -> replay: true, one consequence
    TE-103  late ACK                                -> bounded wait, no silent hang
    TE-104  receipt retrieval after transport loss  -> sealed receipt via path B
    TE-105  provider identity vs transport identity -> provider/authority invariant
               on both paths; only transport names differ
  """

  use ExUnit.Case, async: true

  alias ChatGPTCloud.Xaas.{Receipt, Runner, Target}
  alias ChatGPTCloud.Xaas.Test.ContractServer
  alias ChatGPTCloud.Xaas.Test.InProcTransport, as: InProc
  alias ChatGPTCloud.Xaas.Transport.Http

  @moduletag :tmp_dir

  # --- substrates -----------------------------------------------------------

  # Plain start_supervised server: enough when the path is never killed.
  defp server(config), do: ContractServer.start(&start_supervised!/1, config)

  # Killable substrate: the TCP listener lives under OUR OWN supervisor (so it can
  # be terminated mid-episode) while the epoch-store agent survives it -- exactly
  # the extinction shape: the transport dies, the execution substrate does not.
  defp substrate(config) do
    {:ok, sup} = Supervisor.start_link([], strategy: :one_for_one)

    srv =
      ContractServer.start(
        fn spec ->
          {:ok, pid} = Supervisor.start_child(sup, spec)
          pid
        end,
        config
      )

    {sup, srv}
  end

  # Genuinely close the PATH A TCP listener: stop the supervisor that owns the
  # Bandit tree. The epoch-store agent is linked to the test process, not to this
  # supervisor, so the execution substrate survives exactly the transport.
  defp kill_transport(sup), do: Supervisor.stop(sup, :normal)

  defp extinct?(target) do
    match?({:error, {:network, _}}, Http.request(:get, "/internal-api/fabric/probe", nil, target: target))
  end

  defp wait_until(fun, tries \\ 20)

  defp wait_until(_fun, 0), do: flunk("condition never became true")

  defp wait_until(fun, tries) do
    if fun.(), do: :ok, else: (Process.sleep(50) && wait_until(fun, tries - 1))
  end

  # --- fixtures -------------------------------------------------------------

  defp target(srv), do: Target.resolve(%{"XAAS_MCP_URL" => srv.mcp_url, "XAAS_MCP_TOKEN" => srv.token})

  # Bind PATH B's in-process router to this substrate's base URL for the test's
  # duration (the Runner builds its own transport opts, so the binding is mounted,
  # not passed per request). Returns [] so it composes into runner opts.
  defp mount(srv) do
    {:ok, base} = Target.base_url(target(srv))
    InProc.mount(base, {ContractServer.Router, [agent: srv.agent]})
    on_exit(fn -> InProc.unmount(base) end)
    []
  end

  defp opts(ctx, extra \\ []),
    do: Keyword.merge([journal_dir: ctx.tmp_dir, timeout: 2_000, wait_ms: 50, max_steps: 12], extra)

  defp req(key), do: %{"goal" => "fixture goal #{key}", "idempotency_key" => key}

  defp timed(fun) do
    {micros, value} = :timer.tc(fun)
    {div(micros, 1000), value}
  end

  # --- normalized receipt schema --------------------------------------------

  # Volatile fields: wall-clock and self-digest. Everything else must be
  # schema-identical across transport paths (only transport/provider-namespaced
  # fields may differ; the in-proc path shares even the endpoint identity here).
  defp strip_volatile(receipt), do: Map.drop(receipt, ["receipt_sha256", "observed_at"])

  defp same_shape(l, r) when is_map(l) and is_map(r),
    do:
      MapSet.new(Map.keys(l)) == MapSet.new(Map.keys(r)) and
        Enum.all?(Map.keys(l), fn k -> same_shape(l[k], r[k]) end)

  defp same_shape(l, r) when is_list(l) and is_list(r),
    do: length(l) == length(r) and Enum.all?(Enum.zip(l, r), fn {a, b} -> same_shape(a, b) end)

  defp same_shape(l, r) when is_binary(l) and is_binary(r), do: true
  defp same_shape(l, r) when is_integer(l) and is_integer(r), do: true
  defp same_shape(l, r) when is_boolean(l) and is_boolean(r), do: true
  defp same_shape(nil, nil), do: true

  # Nullable annotation: a field present on one path and nil on the other is the
  # same schema (e.g. the submit step records reason "IDEMPOTENT_REPLAY" only
  # when the run was replayed; a fresh run records nil). Scalar-only on purpose:
  # a value that is a map/list on one side and nil on the other is still a
  # divergence, and a wrong-typed value on both paths is still a divergence.
  defp same_shape(nil, r) when is_binary(r) or is_integer(r) or is_boolean(r), do: true
  defp same_shape(l, nil) when is_binary(l) or is_integer(l) or is_boolean(l), do: true

  defp same_shape(_, _), do: false

  # --- fault matrix -----------------------------------------------------------

  test "TE-001 transport unavailable at start: typed BLOCKED(NETWORK), bounded", ctx do
    {:ok, sock} = :gen_tcp.listen(0, ip: :loopback)
    {:ok, port} = :inet.port(sock)
    :ok = :gen_tcp.close(sock)

    t = Target.resolve(%{"XAAS_MCP_URL" => "http://127.0.0.1:#{port}/internal-api/execution/mcp", "XAAS_MCP_TOKEN" => "te-001"})

    {elapsed_ms, {state, receipt}} =
      timed(fn -> Runner.run(Http, t, req("te-001-unavailable-s042"), opts(ctx, timeout: 1_000)) end)

    assert state.phase == {:blocked, "NETWORK"}
    assert {receipt["standing"], receipt["reason"]} == {"BLOCKED", "NETWORK"}
    assert [%{"step" => "probe", "standing" => "BLOCKED"}] = receipt["consequence"]["trace"]
    assert elapsed_ms < 2_000, "unavailable transport must fail bounded, took #{elapsed_ms}ms"
  end

  test "TE-002 mid-flight drop on path A: typed failure, the run IS recorded", ctx do
    srv = server(%{drop_first_submit_ms: 800})
    key = "te-002-midflight-s007"

    {crashed, receipt} = Runner.run(Http, target(srv), req(key), opts(ctx, timeout: 300))

    assert crashed.phase == {:blocked, "NETWORK"}
    assert crashed.epoch_id == nil
    assert {receipt["standing"], receipt["reason"]} == {"BLOCKED", "NETWORK"}
    # The ACK was lost, the work was not: the substrate holds the run.
    assert %{} = ContractServer.runs(srv)[key]

    journal = ctx.tmp_dir |> Path.join(key <> ".json") |> File.read!() |> JSON.decode!()
    assert journal["request"]["idempotency_key"] == key
  end

  test "TE-003 restart on the OTHER transport: same key, same epoch, replay: true", ctx do
    srv = server(%{drop_first_submit_ms: 800, polls: [:sealed]})
    key = "te-003-restart-s013"

    {_crashed, _} = Runner.run(Http, target(srv), req(key), opts(ctx, timeout: 300))
    recorded = ContractServer.runs(srv)[key]

    Process.sleep(500)

    # Restart over PATH B (in-process): the journal is the only thing carried over.
    {resumed, receipt} = Runner.resume(InProc, target(srv), key, opts(ctx, mount(srv)))

    assert resumed.phase == :replayed
    assert resumed.resumed? and resumed.replay?
    assert resumed.epoch_id == recorded.epoch_id
    assert receipt["standing"] == "ALIVE"
    assert receipt["consequence"]["idempotent_replay"] == true
    # One run, one epoch, one consequence -- never a second one.
    assert map_size(ContractServer.runs(srv)) == 1
  end

  test "TE-100 TRANSPORT-EXTINCTION-001: path A killed between submit and receipt, execution continues on path B", ctx do
    {sup, srv} = substrate(%{polls: [:timeout, :sealed]})
    key = "te-100-extinction-s001"
    t = target(srv)

    # PATH A: probe, admit, submit (journal written at submit), then the episode is
    # interrupted: the transport path dies before any receipt was observed.
    {submitted, partial_a} = Runner.run(Http, t, req(key), opts(ctx, max_steps: 3))

    assert submitted.phase == :submitted
    assert submitted.epoch_id
    assert {partial_a["standing"], partial_a["reason"]} == {"PARTIAL_ALIVE", "AWAITING_SEAL"}
    epoch = submitted.epoch_id

    kill_transport(sup)
    wait_until(fn -> extinct?(t) end)

    # PATH B: same work-order identity resumes through a transport that never
    # existed as a socket; the substrate answers with the SAME epoch (replay).
    {resumed, receipt} = Runner.resume(InProc, t, key, opts(ctx, mount(srv)))

    assert resumed.phase == :replayed
    assert resumed.resumed? and resumed.replay?
    assert resumed.epoch_id == epoch
    assert {receipt["standing"], receipt["reason"], receipt["authority"]} == {"ALIVE", nil, "CONSTRUCT"}
    assert receipt["consequence"]["idempotent_replay"] == true

    # Same WorkOrder identity across paths: ONE run, ONE epoch, ONE consequence.
    runs = ContractServer.runs(srv)
    assert map_size(runs) == 1
    assert runs[key].epoch_id == epoch

    # Same normalized receipt schema on both paths: a shadow episode driven purely
    # on PATH B must produce the same shape and the same invariant fields.
    {shadow_state, shadow_receipt} =
      Runner.run(InProc, t, req("te-100-shadow-s001"), opts(ctx, mount(srv)))

    assert shadow_state.phase == :replayed

    a = strip_volatile(receipt)
    b = strip_volatile(shadow_receipt)

    assert same_shape(a, b)

    for field <- ~w(schema subject standing_scope authority standing reason authenticated endpoint endpoint_sha256),
        do: assert(a[field] == b[field], "invariant field #{field} diverged across paths")

    assert Enum.map(a["consequence"]["trace"], & &1["step"]) ==
             Enum.map(b["consequence"]["trace"], & &1["step"])
  end

  test "TE-101 anti-vacuity: the court CAN fail (broken seal refused on path B, schema comparator refuses divergence)", ctx do
    srv = server(%{tamper: true})
    {state, receipt} =
      Runner.run(InProc, target(srv), req("te-101-antivacuity-s021"), opts(ctx, mount(srv)))

    assert state.phase == {:refused, "replay_digest_mismatch"}
    assert {receipt["standing"], receipt["reason"]} == {"REFUSED", "replay_digest_mismatch"}

    # The schema comparator is not vacuously true either.
    refute same_shape(%{"a" => 1}, %{"a" => 1, "b" => 2})
    refute same_shape(%{"a" => 1}, %{"a" => "string"})
    refute same_shape([1], [1, 2])
    assert same_shape(strip_volatile(%{"x" => 1, "receipt_sha256" => "z"}), %{"x" => 1})
    # Nullable annotation compatibility is scalar-only, pinned in both directions:
    assert same_shape(%{"a" => nil}, %{"a" => "IDEMPOTENT_REPLAY"})
    assert same_shape(%{"a" => 3}, %{"a" => nil})
    refute same_shape(%{"a" => nil}, %{"a" => %{"nested" => 1}})
    refute same_shape(%{"a" => nil}, %{"a" => [1]})
  end

  test "TE-102 duplicate submission across transports: replay: true, not a second consequence", ctx do
    srv = server(%{polls: [:sealed]})
    key = "te-102-duplicate-s033"

    {first, _} = Runner.run(Http, target(srv), req(key), opts(ctx, max_steps: 3))
    assert first.phase == :submitted

    # The duplicate arrives through the OTHER transport path with the same key.
    {second, _} = Runner.run(InProc, target(srv), req(key), opts(ctx, mount(srv) ++ [max_steps: 3]))
    assert second.phase == :submitted
    assert second.epoch_id == first.epoch_id
    assert Enum.any?(second.trace, &(&1["step"] == "submit" and &1["reason"] == "IDEMPOTENT_REPLAY"))

    assert map_size(ContractServer.runs(srv)) == 1
  end

  test "TE-103 late ACK: bounded typed failure, never a silent hang, reconciled by replay", ctx do
    srv = server(%{drop_first_submit_ms: 500, polls: [:sealed]})
    key = "te-103-lateack-s055"

    {elapsed_ms, {crashed, _}} =
      timed(fn -> Runner.run(Http, target(srv), req(key), opts(ctx, timeout: 200)) end)

    assert crashed.phase == {:blocked, "NETWORK"}
    assert elapsed_ms < 2_000, "late ACK must be a bounded typed failure, took #{elapsed_ms}ms"
    # The ACK lands after the client gave up -- at the substrate, not the client.
    assert %{} = ContractServer.runs(srv)[key]

    Process.sleep(400)

    {resumed, receipt} = Runner.resume(InProc, target(srv), key, opts(ctx, mount(srv)))
    assert resumed.phase == :replayed and resumed.replay?
    assert receipt["consequence"]["idempotent_replay"] == true
    assert map_size(ContractServer.runs(srv)) == 1
  end

  test "TE-104 sealed receipt retrievable on path B after path A is extinct", ctx do
    {sup, srv} = substrate(%{polls: [:sealed]})
    key = "te-104-receipt-after-loss-s077"
    t = target(srv)

    {submitted, _} = Runner.run(Http, t, req(key), opts(ctx, max_steps: 3))
    epoch = submitted.epoch_id

    kill_transport(sup)
    wait_until(fn -> extinct?(t) end)

    # No resume, no replay of the episode: a bare receipt retrieval over PATH B
    # (router bound per-request through the supported :plug opt).
    path = "/internal-api/fabric/epochs/#{epoch}/receipts?wait_ms=50"

    assert {:ok, 200, body} =
             InProc.request(:get, path, nil,
               target: t,
               plug: {ContractServer.Router, [agent: srv.agent]}
             )
    assert body["state"] == "sealed"

    assert [%{"receipt" => sealed, "digest" => digest}] = body["receipts"]
    assert sealed["epoch_id"] == epoch
    assert sealed["standing"] == "ALIVE"
    assert Receipt.verify_replay(sealed, digest) == :ok
  end

  test "TE-105 provider identity and authority ceiling are transport-invariant; transport identity is not", ctx do
    srv = server(%{polls: [:sealed]})
    key = "te-105-identity-s088"
    t = target(srv)

    {_state_a, receipt_a} = Runner.run(Http, t, req(key <> "-a"), opts(ctx))
    {_state_b, receipt_b} = Runner.run(InProc, t, req(key <> "-b"), opts(ctx, mount(srv)))

    # Provider identity: always "zcode", on both paths, in the request actually sent.
    for {receipt, transport, journal_key} <- [
          {receipt_a, Http, key <> "-a"},
          {receipt_b, InProc, key <> "-b"}
        ] do
      journal = ctx.tmp_dir |> Path.join(journal_key <> ".json") |> File.read!() |> JSON.decode!()
      assert journal["request"]["provider"] == "zcode"
      assert receipt["authority"] == "CONSTRUCT"
      assert receipt["endpoint_sha256"] == Receipt.endpoint_digest(srv.mcp_url)
      # The transport is the runner's argument, not a field of the work order:
      # both receipts are schema chatgpt-cloud.xaas-fabric-receipt/1 regardless.
      assert receipt["schema"] == "chatgpt-cloud.xaas-fabric-receipt/1"
      assert transport in [Http, InProc]
    end

    # The DO verb is refused by authority ceiling on BOTH paths.
    assert {:ok, 403, %{"reason" => "authority_ceiling:actuate"}} =
             InProc.request(:post, "/internal-api/fabric/actuate", %{}, target: t)

    assert {:ok, 403, %{"reason" => "authority_ceiling:actuate"}} =
             Http.request(:post, "/internal-api/fabric/actuate", %{}, target: t)
  end
end
