defmodule ChatGPTCloud.Xaas.Test.InProcTransport do
  @moduledoc """
  SECOND TRANSPORT PATH (test support only). Implements the same
  `ChatGPTCloud.Xaas.Transport` behaviour as `ChatGPTCloud.Xaas.Transport.Http`,
  but opens no socket: the request is dispatched in-process into a Plug router
  (`opts[:plug] = {router_module, router_opts}`), producing identical
  `xaas-fabric/1` wire shapes -- same paths, same canonical JSON bodies, same
  statuses.

  Exists so the transport-extinction court can prove that execution semantics are
  independent of transport semantics: ONE pure `ChatGPTCloud.Xaas.Fabric` state
  machine, TWO transport identities, identical normalized receipts.

  Request bodies use the same canonical JSON as the HTTP transport; responses are
  decoded by the same rules (`""`/empty body -> nil; invalid JSON is a typed
  `{:protocol, _}` error); a router that returns without sending a response is a
  typed `{:protocol, :no_response}` error, never a silent success. The target is
  still validated through `Target.base_url/1` so a bad config fails typed on both
  paths. Unlike the HTTP transport there is no URL to open, so scheme/userinfo
  refusals do not apply here (there is no bearer replay risk on a socket that
  never exists).
  """

  @behaviour ChatGPTCloud.Xaas.Transport

  alias ChatGPTCloud.Xaas.{Receipt, Target}

  @doc """
  Bind the in-process router to a XaaS base URL (the `Target.base_url/1` shape,
  e.g. `http://127.0.0.1:PORT`). `ChatGPTCloud.Xaas.Runner` builds its own
  transport opts, so a runner-driven episode cannot pass `:plug` per request;
  a mounted binding makes path B reachable through the standard runner loop.
  """
  def mount(base_url, {router, router_opts} = binding)
      when is_binary(base_url) and is_atom(router) and is_list(router_opts) do
    :persistent_term.put({__MODULE__, base_url}, binding)
  end

  @doc "Remove a mounted binding."
  def unmount(base_url) when is_binary(base_url), do: :persistent_term.erase({__MODULE__, base_url})

  @impl true
  def request(method, path, body, opts) do
    target = Keyword.fetch!(opts, :target)

    with {:ok, base} <- Target.base_url(target),
         {:ok, {router, router_opts}} <- binding(opts, base) do
      method
      |> dispatch(path, body, target, router, router_opts)
      |> respond()
    end
  end

  defp binding(opts, base) do
    case Keyword.fetch(opts, :plug) do
      {:ok, {router, router_opts}} ->
        {:ok, {router, router_opts}}

      :error ->
        # A mounted binding must come back wrapped like the :plug path, or the
        # caller's `with {:ok, ...}` falls through and leaks the raw router
        # tuple as if it were a transport result (typed-result repair,
        # ALOOP-ZCODE-DOGFOOD-001 LANE 4).
        case :persistent_term.get({__MODULE__, base}, :not_mounted) do
          :not_mounted -> {:error, {:config, :router_not_configured}}
          found -> {:ok, found}
        end
    end
  end

  defp dispatch(method, path, body, target, router, router_opts) do
    base_conn =
      %Plug.Conn{}
      |> Plug.Conn.put_req_header("accept", "application/json")
      |> put_authorization(target)

    conn =
      case {method, body} do
        {:get, _} ->
          Plug.Adapters.Test.Conn.conn(base_conn, method, path, nil)

        {:post, b} ->
          base_conn
          |> Plug.Conn.put_req_header("content-type", "application/json")
          |> Plug.Adapters.Test.Conn.conn(method, path, Receipt.canonical(b || %{}))
      end

    router.call(conn, router.init(router_opts))
  end

  defp put_authorization(conn, %{authorization: nil}), do: conn
  defp put_authorization(conn, %{authorization: auth}), do: Plug.Conn.put_req_header(conn, "authorization", auth)

  defp respond(%Plug.Conn{status: nil}), do: {:error, {:protocol, :no_response}}

  defp respond(%Plug.Conn{status: status, resp_body: body}) when body in [nil, ""],
    do: {:ok, status, nil}

  defp respond(%Plug.Conn{status: status, resp_body: raw}) do
    case JSON.decode(raw) do
      {:ok, payload} -> {:ok, status, payload}
      {:error, e} -> {:error, {:protocol, {:invalid_json, status, e}}}
    end
  end
end
