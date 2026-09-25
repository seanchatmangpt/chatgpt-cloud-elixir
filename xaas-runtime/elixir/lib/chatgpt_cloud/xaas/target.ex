defmodule ChatGPTCloud.Xaas.Target do
  @moduledoc """
  Where and as whom the client speaks. Derived from the same environment names as
  Python `scripts/xaas-runtime.py` (`XAAS_MCP_URL`, `XAAS_MCP_TOKEN`) so no new secret
  name exists. The bearer lives only in this struct and in the outgoing request
  header; receipts carry `authenticated: true|false`, never the token.
  """

  @suffix "/internal-api/execution/mcp"
  @default_mcp_url "http://localhost:4000" <> @suffix

  @enforce_keys [:mcp_url]
  defstruct [:mcp_url, :authorization]

  @type t :: %__MODULE__{mcp_url: String.t(), authorization: String.t() | nil}

  @doc "Resolve from an env map (defaults to the process environment) and optional URL flag."
  @spec resolve(map() | nil, String.t() | nil) :: t()
  def resolve(env \\ nil, url \\ nil) do
    env = env || System.get_env()
    mcp_url = String.trim(url || blank_to_nil(env["XAAS_MCP_URL"]) || @default_mcp_url)
    token = String.trim(env["XAAS_MCP_TOKEN"] || "")

    %__MODULE__{
      mcp_url: mcp_url,
      authorization: if(token == "", do: nil, else: "Bearer " <> token)
    }
  end

  @doc "Environment names that are missing (Python `missing_config`)."
  @spec missing_config(map() | nil, String.t() | nil) :: [String.t()]
  def missing_config(env \\ nil, url \\ nil) do
    env = env || System.get_env()

    [
      {"XAAS_MCP_URL", url || env["XAAS_MCP_URL"]},
      {"XAAS_MCP_TOKEN", env["XAAS_MCP_TOKEN"]}
    ]
    |> Enum.filter(fn {_, v} -> String.trim(v || "") == "" end)
    |> Enum.map(&elem(&1, 0))
  end

  @doc """
  Base URL exactly like Python `Target.base_url`: the MCP URL must end in
  `/internal-api/execution/mcp`; the prefix before it is the XaaS base.
  """
  @spec base_url(t()) :: {:ok, String.t()} | {:error, {:config, :mcp_url_suffix}}
  def base_url(%__MODULE__{mcp_url: url}) do
    uri = URI.parse(url)
    path = String.trim_trailing(uri.path || "", "/")

    if String.ends_with?(path, @suffix) do
      prefix = String.slice(path, 0, String.length(path) - String.length(@suffix))
      authority = authority(url)
      {:ok, "#{uri.scheme}://#{authority}#{prefix}"}
    else
      {:error, {:config, :mcp_url_suffix}}
    end
  end

  defp authority(url) do
    case Regex.run(~r{^[A-Za-z][A-Za-z0-9+.-]*://([^/?#]*)}, url) do
      [_, a] -> a
      _ -> ""
    end
  end

  defp blank_to_nil(nil), do: nil
  defp blank_to_nil(v), do: if(String.trim(v) == "", do: nil, else: v)
end
