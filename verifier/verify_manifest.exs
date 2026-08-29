[path] = System.argv()
body = File.read!(path)

# Real JSON parsing via Elixir's built-in JSON module (stdlib since Elixir
# 1.18.0, wrapping OTP 27's :json -- see
# https://hexdocs.pm/elixir/1.18.0/JSON.html). Both capsule families that
# invoke this script pin Elixir/OTP versions at or above that floor:
# versions.toml's [runtime] (Elixir 1.20.2 / OTP 29.0, for beam-core/ash-*/
# autonomic-manufacturing) and capsules/process-intelligence/capsule.toml's
# own separate pin (Elixir 1.18.4 / OTP 27.2.4) -- so JSON.decode/1 is
# available at every version this script actually runs under. No dependency
# is added: JSON is part of the language distribution, not a Hex package.
manifest =
  case JSON.decode(body) do
    {:ok, %{} = decoded} ->
      decoded

    {:ok, _not_an_object} ->
      IO.puts(:stderr, "BUILD_BROKEN: manifest is not a JSON object")
      System.halt(65)

    {:error, reason} ->
      IO.puts(:stderr, "BUILD_BROKEN: manifest is not valid JSON: #{inspect(reason)}")
      System.halt(65)
  end

required = [
  "schema_version",
  "capsule_name",
  "source_sha",
  "platform",
  "runtime",
  "packages",
  "acceptance",
  "dependency_lock_sha256"
]

missing = Enum.reject(required, &Map.has_key?(manifest, &1))

if missing != [] do
  IO.puts(:stderr, "BUILD_BROKEN: manifest missing keys #{inspect(missing)}")
  System.halt(65)
end

versions_path = Path.join([Path.dirname(path), "source", "versions.toml"])

release_version =
  with {:ok, versions_body} <- File.read(versions_path),
       [_, version] <- Regex.run(~r/\[release\]\s+version\s*=\s*"([^"]+)"/m, versions_body),
       true <- Regex.match?(~r/^\d+\.\d+\.\d+$/, version) do
    version
  else
    _ ->
      IO.puts(:stderr, "BUILD_BROKEN: embedded versions.toml has no valid release.version")
      System.halt(65)
  end

sha = :crypto.hash(:sha256, body) |> Base.encode16(case: :lower)
IO.puts("manifest=ALIVE release=#{release_version} sha256=#{sha}")
