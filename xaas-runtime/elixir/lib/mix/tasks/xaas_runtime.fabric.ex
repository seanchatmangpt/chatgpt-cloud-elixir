defmodule Mix.Tasks.XaasRuntime.Fabric do
  @shortdoc "Probe, admit, submit, await and replay one XaaS fabric run; write a receipt"
  @moduledoc """
  Drive one run through the XaaS bounded runtime fabric and write a receipt.

      XAAS_MCP_URL=https://<host>/internal-api/execution/mcp XAAS_MCP_TOKEN=<token> \\
        mix xaas_runtime.fabric --goal "<goal>" --idempotency-key <key> \\
          [--exact-subject <s>] [--worktree <xaas-host-path>] [--resume] \\
          [--timeout-ms 15000] [--wait-ms 25000] [--max-steps 12] \\
          [--receipt-dir ../receipts] [--journal-dir ../journal] [--url <mcp-url>]

  Missing `XAAS_MCP_URL`/`XAAS_MCP_TOKEN` is `BLOCKED(IRREDUCIBLE_TRANSPORT_CONFIG)`,
  never a silent localhost fallback. The receipt redacts the endpoint host (scheme +
  path + sha256) and carries `authenticated`, never the token. Exit codes follow
  Python `scripts/xaas-runtime.py`: 0 ALIVE/PARTIAL_ALIVE, 77 REFUSED*, 64
  UNSUPPORTED, 65 BUILD_BROKEN, 69 otherwise.
  """
  use Mix.Task

  alias ChatGPTCloud.Xaas.{Receipt, Runner, Target}
  alias ChatGPTCloud.Xaas.Transport.Http

  @switches [
    goal: :string,
    idempotency_key: :string,
    exact_subject: :string,
    worktree: :string,
    resume: :boolean,
    timeout_ms: :integer,
    wait_ms: :integer,
    max_steps: :integer,
    receipt_dir: :string,
    journal_dir: :string,
    url: :string
  ]

  @impl Mix.Task
  def run(argv) do
    {opts, _rest, _invalid} = OptionParser.parse(argv, strict: @switches)
    Application.ensure_all_started(:xaas_runtime_client)
    receipt = execute(opts, System.get_env())
    path = write_receipt(opts, receipt)
    Mix.shell().info(Receipt.canonical(receipt))
    Mix.shell().info("receipt: " <> path)
    code = exit_code(receipt["standing"])
    if code != 0, do: exit({:shutdown, code})
    :ok
  end

  @doc false
  def execute(opts, env) do
    case Target.missing_config(env, opts[:url]) do
      [] ->
        target = Target.resolve(env, opts[:url])
        key = opts[:idempotency_key] || ""

        run_opts = [
          journal_dir: opts[:journal_dir] || Path.expand("../journal"),
          timeout: opts[:timeout_ms] || 15_000,
          wait_ms: opts[:wait_ms] || 25_000,
          max_steps: opts[:max_steps] || 12
        ]

        result =
          if opts[:resume],
            do: Runner.resume(Http, target, key, run_opts),
            else: Runner.run(Http, target, request(opts), run_opts)

        case result do
          {:error, :no_journal} -> local("REFUSED_REQUEST", "JOURNAL_NOT_FOUND", key)
          {_state, receipt} -> receipt
        end

      missing ->
        local("BLOCKED", "IRREDUCIBLE_TRANSPORT_CONFIG", opts[:idempotency_key])
        |> Map.put("detail", "missing environment: " <> Enum.join(missing, ","))
        |> Map.delete("receipt_sha256")
        |> then(&Map.put(&1, "receipt_sha256", Receipt.digest(&1)))
    end
  end

  defp request(opts) do
    %{"goal" => opts[:goal], "idempotency_key" => opts[:idempotency_key]}
    |> put_opt("exact_subject", opts[:exact_subject])
    |> put_opt("worktree", opts[:worktree])
  end

  defp put_opt(map, _k, nil), do: map
  defp put_opt(map, k, v), do: Map.put(map, k, v)

  defp local(standing, reason, key) do
    Receipt.build(%{
      "identity" => %{"idempotency_key" => key},
      "consequence" => %{"phase" => "local"},
      "endpoint" => nil,
      "authenticated" => false,
      "standing" => standing,
      "reason" => reason,
      "observed_at" => DateTime.utc_now() |> DateTime.truncate(:second) |> DateTime.to_iso8601(),
      "replay" =>
        "cd xaas-runtime/elixir && mix xaas_runtime.fabric --goal <goal> --idempotency-key <key>"
    })
  end

  defp write_receipt(opts, receipt) do
    dir = opts[:receipt_dir] || Path.expand("../receipts")
    ts = Calendar.strftime(DateTime.utc_now(), "%Y%m%dT%H%M%SZ")
    path = Path.join(dir, "#{ts}-fabric.receipt.json")
    File.mkdir_p!(dir)
    File.write!(path, Receipt.canonical(receipt) <> "\n")
    path
  end

  @doc false
  def exit_code(s) when s in ["ALIVE", "PARTIAL_ALIVE"], do: 0
  def exit_code("REFUSED" <> _), do: 77
  def exit_code("UNSUPPORTED"), do: 64
  def exit_code("BUILD_BROKEN"), do: 65
  def exit_code(_), do: 69
end
