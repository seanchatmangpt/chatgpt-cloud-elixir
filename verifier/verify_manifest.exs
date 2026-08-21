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

sha = :crypto.hash(:sha256, body) |> Base.encode16(case: :lower)
IO.puts("manifest=ALIVE sha256=#{sha}")
