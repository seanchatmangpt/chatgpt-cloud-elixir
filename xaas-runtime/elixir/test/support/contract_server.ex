defmodule ChatGPTCloud.Xaas.Test.ContractServer do
  @moduledoc """
  CONTRACT FIXTURE SERVER (test support only; not XaaS).

  A real Bandit listener on `127.0.0.1:<ephemeral>` serving the `xaas-fabric/1`
  HTTP contract shared with the XaaS `/internal-api/fabric` scope:

      GET  /internal-api/fabric/probe
      POST /internal-api/fabric/admit                          {"capabilities": [...]}
      POST /internal-api/fabric/runs                           {"idempotency_key": ..., ...}
      GET  /internal-api/fabric/epochs/:id/receipts?wait_ms=&after=   (204 on timeout)
      POST /internal-api/fabric/actuate                        -> 403 REFUSED(authority_ceiling:actuate)

  The client under test talks to it over real loopback sockets through
  `:httpc`; nothing owned by the client is replaced. It proves the client against
  the contract as written here, not against XaaS itself: the live leg (P4 B4)
  is the true contract test. Knobs (`config`) exist so one server can produce each
  typed outcome: status override, redirect, slow responses, a dropped first submit
  response (crash window), long-poll scripts, and a tampered seal digest.
  """

  alias ChatGPTCloud.Xaas.Receipt

  @allowlist ~w(fabric.probe run.submit epoch.receipts)

  @doc "Start a fixture server under the test supervisor; returns `%{url, port, agent}`."
  def start(test_ctx_start_supervised, config \\ %{}) do
    {:ok, agent} =
      Agent.start_link(fn ->
        %{config: default_config(config), runs: %{}, polls: %{}, log: []}
      end)

    pid =
      test_ctx_start_supervised.(
        Supervisor.child_spec(
          {Bandit,
           plug: {__MODULE__.Router, agent: agent}, port: 0, ip: :loopback, startup_log: false},
          id: make_ref()
        )
      )

    {:ok, {_ip, port}} = ThousandIsland.listener_info(pid)

    %{
      agent: agent,
      port: port,
      mcp_url: "http://127.0.0.1:#{port}/internal-api/execution/mcp",
      token: Agent.get(agent, & &1.config.token)
    }
  end

  @doc "Every request the server saw: `{method, path, authorization}`."
  def log(%{agent: agent}), do: Agent.get(agent, &Enum.reverse(&1.log))

  @doc "Runs recorded by idempotency key."
  def runs(%{agent: agent}), do: Agent.get(agent, & &1.runs)

  defp default_config(config) do
    Map.merge(
      %{
        token: "fixture-token",
        status_override: nil,
        redirect_to: nil,
        slow_ms: nil,
        drop_first_submit_ms: nil,
        polls: [:sealed],
        tamper: false,
        capabilities: @allowlist,
        admit_only: nil
      },
      config
    )
  end

  @doc false
  def sealed_receipt(run) do
    %{
      "schema" => "xaas.fabric-sealed-receipt/1",
      "run_id" => run.run_id,
      "epoch_id" => run.epoch_id,
      "exact_subject" => run.exact_subject,
      "outcome" => "alive",
      "final_head" => "0000000000000000000000000000000000000000",
      "authority" => "CONSTRUCT",
      "standing" => "ALIVE"
    }
  end

  defmodule Router do
    @moduledoc false
    use Plug.Router, copy_opts_to_assign: :fixture

    alias ChatGPTCloud.Xaas.Test.ContractServer

    plug(:record)
    plug(:authenticate)
    plug(:match)
    plug(Plug.Parsers, parsers: [:json], json_decoder: JSON, pass: ["application/json"])
    plug(:dispatch)

    get "/internal-api/fabric/probe" do
      cfg = config(conn)

      cond do
        cfg.redirect_to ->
          conn |> put_resp_header("location", cfg.redirect_to) |> send_resp(302, "")

        cfg.slow_ms ->
          Process.sleep(cfg.slow_ms)
          json(conn, 200, probe_body(cfg))

        true ->
          json(conn, 200, probe_body(cfg))
      end
    end

    post "/internal-api/fabric/admit" do
      cfg = config(conn)
      requested = List.wrap(conn.body_params["capabilities"])
      allowed = cfg.admit_only || cfg.capabilities

      admitted = Enum.filter(requested, &(&1 in allowed))

      refused =
        for verb <- requested, verb not in allowed do
          [verb, if(verb == "actuate", do: "authority_ceiling", else: "capability_not_admitted")]
        end

      json(conn, 200, %{"admitted" => admitted, "refused" => refused})
    end

    post "/internal-api/fabric/runs" do
      key = conn.body_params["idempotency_key"]

      if is_binary(key) and key != "" do
        agent = conn.assigns.fixture[:agent]

        {status, run, drop_ms} =
          Agent.get_and_update(agent, fn st ->
            case st.runs[key] do
              nil ->
                run = %{
                  run_id: uuid(),
                  epoch_id: uuid(),
                  exact_subject: "fabric:fixture-org:#{key}",
                  goal: conn.body_params["goal"]
                }

                drop = st.config.drop_first_submit_ms

                st = %{
                  st
                  | runs: Map.put(st.runs, key, run),
                    polls: Map.put(st.polls, run.epoch_id, st.config.polls)
                }

                {{201, run, drop}, put_in(st.config.drop_first_submit_ms, nil)}

              run ->
                {{200, run, nil}, st}
            end
          end)

        # Crash window: the run is recorded, but the response never reaches the client in time.
        if drop_ms, do: Process.sleep(drop_ms)

        json(conn, status, %{
          "run_id" => run.run_id,
          "epoch_id" => run.epoch_id,
          "exact_subject" => run.exact_subject,
          "replay" => status == 200
        })
      else
        json(conn, 422, %{"standing" => "REFUSED", "reason" => "idempotency_key_required"})
      end
    end

    get "/internal-api/fabric/epochs/:epoch_id/receipts" do
      agent = conn.assigns.fixture[:agent]
      conn = Plug.Conn.fetch_query_params(conn)
      wait_ms = min(String.to_integer(conn.query_params["wait_ms"] || "25000"), 25_000)

      {step, run, tamper} =
        Agent.get_and_update(agent, fn st ->
          run = Enum.find_value(st.runs, fn {_k, r} -> if r.epoch_id == epoch_id, do: r end)

          case st.polls[epoch_id] do
            nil -> {{:unknown, nil, false}, st}
            [only] -> {{only, run, st.config.tamper}, st}
            [h | t] -> {{h, run, st.config.tamper}, put_in(st.polls[epoch_id], t)}
          end
        end)

      case step do
        :unknown ->
          json(conn, 404, %{"standing" => "BLOCKED", "reason" => "epoch_not_visible"})

        :timeout ->
          Process.sleep(wait_ms)
          send_resp(conn, 204, "")

        :leased ->
          json(conn, 200, %{
            "epoch_id" => epoch_id,
            "state" => "leased",
            "receipts" => [],
            "cursor" => nil
          })

        :sealed ->
          sealed = ContractServer.sealed_receipt(run)

          digest =
            Receipt.digest(if tamper, do: Map.put(sealed, "outcome", "tampered"), else: sealed)

          json(conn, 200, %{
            "epoch_id" => epoch_id,
            "state" => "sealed",
            "receipts" => [%{"receipt" => sealed, "digest" => digest}],
            "cursor" => digest
          })
      end
    end

    post "/internal-api/fabric/actuate" do
      json(conn, 403, %{"standing" => "REFUSED", "reason" => "authority_ceiling:actuate"})
    end

    match _ do
      json(conn, 404, %{"standing" => "BLOCKED", "reason" => "not_found"})
    end

    defp record(conn, _opts) do
      auth = conn |> get_req_header("authorization") |> List.first()

      Agent.update(conn.assigns.fixture[:agent], fn st ->
        %{st | log: [{conn.method, conn.request_path, auth} | st.log]}
      end)

      conn
    end

    defp authenticate(conn, _opts) do
      cfg = config(conn)

      cond do
        get_req_header(conn, "authorization") != ["Bearer " <> cfg.token] ->
          conn |> json(401, %{"standing" => "REFUSED", "reason" => "unauthenticated"}) |> halt()

        cfg.status_override ->
          conn
          |> json(cfg.status_override, %{"standing" => "REFUSED", "reason" => "fixture_override"})
          |> halt()

        true ->
          conn
      end
    end

    defp config(conn), do: Agent.get(conn.assigns.fixture[:agent], & &1.config)

    defp probe_body(cfg) do
      %{
        "protocol" => "xaas-fabric/1",
        "capabilities" => cfg.capabilities,
        "refused" => %{"actuate" => "authority_ceiling"},
        "long_poll_max_ms" => 25_000,
        "org_scoped?" => true
      }
    end

    defp json(conn, status, body) do
      conn
      |> put_resp_content_type("application/json")
      |> send_resp(status, JSON.encode!(body))
    end

    defp uuid do
      <<a::32, b::16, c::16, d::16, e::48>> = :crypto.strong_rand_bytes(16)

      :io_lib.format("~8.16.0b-~4.16.0b-~4.16.0b-~4.16.0b-~12.16.0b", [a, b, c, d, e])
      |> IO.iodata_to_binary()
    end
  end
end

defmodule ChatGPTCloud.Xaas.Test.Catcher do
  @moduledoc """
  Second loopback host for the redirect case: records every request it receives so
  the test can prove the bearer never reached it.
  """
  @behaviour Plug

  def start(start_supervised) do
    {:ok, agent} = Agent.start_link(fn -> [] end)

    pid =
      start_supervised.(
        Supervisor.child_spec(
          {Bandit, plug: {__MODULE__, agent: agent}, port: 0, ip: :loopback, startup_log: false},
          id: make_ref()
        )
      )

    {:ok, {_ip, port}} = ThousandIsland.listener_info(pid)
    %{agent: agent, url: "http://127.0.0.1:#{port}/stolen"}
  end

  def seen(%{agent: agent}), do: Agent.get(agent, & &1)

  @impl true
  def init(opts), do: opts

  @impl true
  def call(conn, opts) do
    auth = conn |> Plug.Conn.get_req_header("authorization") |> List.first()
    Agent.update(opts[:agent], &[{conn.method, conn.request_path, auth} | &1])
    Plug.Conn.send_resp(conn, 200, "{}")
  end
end
