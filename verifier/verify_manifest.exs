[path] = System.argv()
body = File.read!(path)

required = [
  "\"schema_version\"",
  "\"capsule_name\"",
  "\"source_sha\"",
  "\"platform\"",
  "\"runtime\"",
  "\"packages\"",
  "\"acceptance\"",
  "\"dependency_lock_sha256\""
]

missing = Enum.reject(required, &String.contains?(body, &1))

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
