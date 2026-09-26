defmodule ChatGPTCloud.Xaas.Transport.Http do
  @moduledoc """
  `:httpc` transport.

    * `autoredirect: false` - a 3xx is refused as `{:redirect, status}`; the bearer is
      never replayed to another location (Python `_RefuseRedirect`).
    * TLS: `verify: :verify_peer` against `:public_key.cacerts_get/0`, hostname checked.
    * URL userinfo and non-http(s) schemes are refused before any socket opens.
  """
  @behaviour ChatGPTCloud.Xaas.Transport

  alias ChatGPTCloud.Xaas.{Receipt, Target}

  @impl true
  def request(method, path, body, opts) do
    target = Keyword.fetch!(opts, :target)
    timeout = Keyword.get(opts, :timeout, 15_000)

    with {:ok, base} <- Target.base_url(target),
         url = base <> path,
         :ok <- admissible_url(url) do
      do_request(method, url, body, target, timeout)
    end
  end

  @doc false
  def admissible_url(url) do
    uri = URI.parse(url)

    cond do
      uri.userinfo != nil ->
        {:error, {:config, :url_userinfo_refused}}

      uri.scheme not in ["http", "https"] or uri.host in [nil, ""] ->
        {:error, {:config, :url_invalid}}

      true ->
        :ok
    end
  end

  defp do_request(method, url, body, target, timeout) do
    headers =
      [{~c"accept", ~c"application/json"}] ++
        if target.authorization,
          do: [{~c"authorization", String.to_charlist(target.authorization)}],
          else: []

    request =
      case {method, body} do
        {:get, _} ->
          {String.to_charlist(url), headers}

        {:post, b} ->
          {String.to_charlist(url), headers, ~c"application/json", Receipt.canonical(b || %{})}
      end

    http_opts = [
      autoredirect: false,
      timeout: timeout,
      connect_timeout: timeout,
      ssl: ssl_opts(url)
    ]

    case :httpc.request(method, request, http_opts, body_format: :binary) do
      {:ok, {{_, status, _}, _headers, _raw}} when status in 300..399 ->
        {:error, {:redirect, status}}

      {:ok, {{_, status, _}, _headers, raw}} ->
        decode(status, raw)

      {:error, reason} ->
        {:error, {:network, reason}}
    end
  end

  defp decode(status, raw) when raw in ["", nil], do: {:ok, status, nil}

  defp decode(status, raw) do
    case JSON.decode(raw) do
      {:ok, payload} -> {:ok, status, payload}
      {:error, e} -> {:error, {:protocol, {:invalid_json, status, e}}}
    end
  end

  defp ssl_opts(url) do
    host = URI.parse(url).host || ""

    [
      verify: :verify_peer,
      cacerts: :public_key.cacerts_get(),
      server_name_indication: String.to_charlist(host),
      customize_hostname_check: [match_fun: :public_key.pkix_verify_hostname_match_fun(:https)]
    ]
  end
end
