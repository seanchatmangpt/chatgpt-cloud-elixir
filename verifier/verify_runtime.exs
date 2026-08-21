[manifest_path] = System.argv()
manifest = File.read!(manifest_path)
root = System.fetch_env!("CAPSULE_ROOT")

extract = fn key ->
  case Regex.run(~r/"#{Regex.escape(key)}"\s*:\s*"([^"]+)"/, manifest) do
    [_, value] -> value
    _ -> nil
  end
end

expected_elixir = extract.("elixir_expected")
expected_otp = extract.("otp_expected")
actual_elixir = System.version()
actual_otp = :erlang.system_info(:otp_release) |> List.to_string()

unless actual_elixir == expected_elixir do
  IO.puts(:stderr, "BUILD_BROKEN: Elixir expected=#{expected_elixir} observed=#{actual_elixir}")
  System.halt(65)
end

unless String.split(actual_otp, ".") |> hd() == String.split(expected_otp, ".") |> hd() do
  IO.puts(:stderr, "BUILD_BROKEN: OTP expected=#{expected_otp} observed=#{actual_otp}")
  System.halt(65)
end

for executable <- ["erl", "elixir", "mix"] do
  path = System.find_executable(executable)
  unless path && String.starts_with?(Path.expand(path), Path.expand(root)) do
    IO.puts(:stderr, "BUILD_BROKEN: #{executable} is not capsule-local: #{inspect(path)}")
    System.halt(65)
  end
end

{mix_output, 0} = System.cmd("mix", ["--version"], stderr_to_stdout: true)
IO.puts("runtime=ALIVE otp=#{actual_otp} elixir=#{actual_elixir}")
IO.write(mix_output)
