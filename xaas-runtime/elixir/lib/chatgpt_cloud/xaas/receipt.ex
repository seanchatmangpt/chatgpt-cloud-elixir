defmodule ChatGPTCloud.Xaas.Receipt do
  @moduledoc """
  Canonical JSON and sha256 digests, byte-identical to Python
  `scripts/xaas-runtime.py` `canonical_json/1`:

      json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()

  Rules (each pinned by `test/fixtures/receipt_golden.json` + `.sha256`):

    * object keys sorted by Unicode code point (UTF-8 byte order is identical);
    * separators `,` and `:` with no whitespace;
    * strings are raw UTF-8; only `"`, `\\` and C0 controls are escaped, using
      `\\b \\f \\n \\r \\t` and lowercase `\\u00xx` for the rest (`/` and DEL are raw);
    * floats are refused: receipts carry integers, strings, booleans, null, lists, maps.

  Receipts carry the BRCE fields identity, authority, consequence, replay, standing.
  """

  @schema "chatgpt-cloud.xaas-fabric-receipt/1"

  def schema, do: @schema

  @doc "Canonical JSON bytes (Python canonical_json parity)."
  @spec canonical(term()) :: binary()
  def canonical(value), do: value |> encode() |> IO.iodata_to_binary()

  @doc "Lowercase hex sha256 of the canonical bytes."
  @spec digest(term()) :: String.t()
  def digest(value), do: :crypto.hash(:sha256, canonical(value)) |> Base.encode16(case: :lower)

  @doc """
  Replay check: recompute the digest of the sealed receipt body and compare it
  with the digest the server declared at seal time.
  """
  @spec verify_replay(map(), String.t()) :: :ok | {:refused, :replay_digest_mismatch}
  def verify_replay(sealed, declared) when is_map(sealed) and is_binary(declared) do
    if digest(sealed) == declared, do: :ok, else: {:refused, :replay_digest_mismatch}
  end

  def verify_replay(_sealed, _declared), do: {:refused, :replay_digest_mismatch}

  @doc """
  Receipt-safe endpoint (Python `endpoint_identity`): scheme + path only; the host is
  secret-derived and receipts are committed to git.
  """
  @spec endpoint_identity(String.t()) :: String.t()
  def endpoint_identity(url) do
    uri = URI.parse(url)
    "#{uri.scheme}://<redacted-host>#{uri.path}"
  end

  @doc "Python `endpoint_digest`: sha256 of scheme://host[:port]path (host lowercased)."
  @spec endpoint_digest(String.t()) :: String.t()
  def endpoint_digest(url) do
    uri = URI.parse(url)
    host = String.downcase(uri.host || "")
    port = if uri.port && port_in_authority?(url, uri.port), do: ":#{uri.port}", else: ""

    :crypto.hash(:sha256, "#{uri.scheme}://#{host}#{port}#{uri.path}")
    |> Base.encode16(case: :lower)
  end

  # Python keeps the port only when it is written in the URL (parsed.port is None otherwise).
  defp port_in_authority?(url, port) do
    case Regex.run(~r{^[A-Za-z][A-Za-z0-9+.-]*://([^/?#]*)}, url) do
      [_, authority] -> String.ends_with?(authority, ":#{port}")
      _ -> false
    end
  end

  @doc """
  Build the client fabric receipt. `receipt_sha256` is the digest of every other field.
  """
  @spec build(map()) :: map()
  def build(fields) when is_map(fields) do
    body =
      %{
        "schema" => @schema,
        "subject" => "xaas-runtime-fabric",
        "standing_scope" => "transport",
        "authority" => "CONSTRUCT"
      }
      |> Map.merge(stringify_keys(fields))

    Map.put(body, "receipt_sha256", digest(body))
  end

  defp stringify_keys(map) do
    Map.new(map, fn {k, v} -> {to_string(k), v} end)
  end

  # --- encoder -------------------------------------------------------------

  defp encode(nil), do: "null"
  defp encode(true), do: "true"
  defp encode(false), do: "false"
  defp encode(v) when is_integer(v), do: Integer.to_string(v)

  defp encode(v) when is_float(v),
    do: raise(ArgumentError, "canonical receipts refuse floats: #{inspect(v)}")

  defp encode(v) when is_atom(v), do: encode_string(Atom.to_string(v))
  defp encode(v) when is_binary(v), do: encode_string(v)

  defp encode(v) when is_list(v),
    do: ["[", v |> Enum.map(&encode/1) |> Enum.intersperse(","), "]"]

  defp encode(v) when is_map(v) do
    pairs =
      v
      |> Enum.map(fn {k, val} -> {key(k), val} end)
      |> Enum.sort_by(fn {k, _} -> k end)

    dupes = length(pairs) - length(Enum.uniq_by(pairs, &elem(&1, 0)))
    if dupes > 0, do: raise(ArgumentError, "canonical receipts refuse duplicate keys")

    body =
      pairs
      |> Enum.map(fn {k, val} -> [encode_string(k), ":", encode(val)] end)
      |> Enum.intersperse(",")

    ["{", body, "}"]
  end

  defp encode(v), do: raise(ArgumentError, "canonical receipts refuse #{inspect(v)}")

  defp key(k) when is_binary(k), do: k
  defp key(k) when is_atom(k) and k not in [nil, true, false], do: Atom.to_string(k)
  defp key(k), do: raise(ArgumentError, "canonical receipts refuse key #{inspect(k)}")

  defp encode_string(s) do
    unless String.valid?(s), do: raise(ArgumentError, "canonical receipts refuse invalid UTF-8")
    [?", escape(s, []), ?"]
  end

  defp escape(<<>>, acc), do: Enum.reverse(acc)
  defp escape(<<?", rest::binary>>, acc), do: escape(rest, ["\\\"" | acc])
  defp escape(<<?\\, rest::binary>>, acc), do: escape(rest, ["\\\\" | acc])
  defp escape(<<?\b, rest::binary>>, acc), do: escape(rest, ["\\b" | acc])
  defp escape(<<?\f, rest::binary>>, acc), do: escape(rest, ["\\f" | acc])
  defp escape(<<?\n, rest::binary>>, acc), do: escape(rest, ["\\n" | acc])
  defp escape(<<?\r, rest::binary>>, acc), do: escape(rest, ["\\r" | acc])
  defp escape(<<?\t, rest::binary>>, acc), do: escape(rest, ["\\t" | acc])

  defp escape(<<c, rest::binary>>, acc) when c < 0x20 do
    hex = c |> Integer.to_string(16) |> String.downcase() |> String.pad_leading(4, "0")
    escape(rest, ["\\u" <> hex | acc])
  end

  defp escape(<<c, rest::binary>>, acc), do: escape(rest, [c | acc])
end
