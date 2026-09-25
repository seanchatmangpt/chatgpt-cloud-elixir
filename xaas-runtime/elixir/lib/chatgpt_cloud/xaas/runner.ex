defmodule ChatGPTCloud.Xaas.Runner do
  @moduledoc """
  The only impure loop: drive `ChatGPTCloud.Xaas.Fabric` through a transport,
  journalling to `<journal_dir>/<idempotency_key>.json` before submit and after its
  response, so `resume/4` can close the crash window with the same key.
  """

  alias ChatGPTCloud.Xaas.{Fabric, Receipt}

  @doc """
  Run `request` to a terminal state or until `max_steps` actions were taken.

  Options: `:journal_dir` (required), `:timeout` (ms, default 15000), `:wait_ms`,
  `:max_steps` (default 12).
  """
  @spec run(module(), ChatGPTCloud.Xaas.Target.t(), map(), keyword()) :: {Fabric.t(), map()}
  def run(transport, target, request, opts) do
    drive(transport, target, Fabric.new(request, Keyword.take(opts, [:wait_ms])), opts)
  end

  @doc "Resume from the journal of `key` after a crash; same key, same epoch."
  @spec resume(module(), ChatGPTCloud.Xaas.Target.t(), String.t(), keyword()) ::
          {Fabric.t(), map()} | {:error, :no_journal}
  def resume(transport, target, key, opts) do
    case File.read(journal_path(opts, key)) do
      {:ok, raw} ->
        journal = JSON.decode!(raw)
        drive(transport, target, Fabric.resume(journal, Keyword.take(opts, [:wait_ms])), opts)

      {:error, _} ->
        {:error, :no_journal}
    end
  end

  @doc "Journal file for an idempotency key."
  def journal_path(opts, key), do: Path.join(Keyword.fetch!(opts, :journal_dir), key <> ".json")

  defp drive(transport, target, state, opts) do
    max_steps = Keyword.get(opts, :max_steps, 12)
    final = loop(transport, target, state, opts, max_steps)

    extra = %{
      "endpoint" => Receipt.endpoint_identity(target.mcp_url),
      "endpoint_sha256" => Receipt.endpoint_digest(target.mcp_url),
      "authenticated" => target.authorization != nil,
      "observed_at" => DateTime.utc_now() |> DateTime.truncate(:second) |> DateTime.to_iso8601()
    }

    {final, Fabric.receipt(final, extra)}
  end

  defp loop(_transport, _target, state, _opts, 0), do: state

  defp loop(transport, target, state, opts, budget) do
    case Fabric.next(state) do
      {:request, method, path, body} ->
        if state.phase == :admitted, do: write_journal(opts, state)

        result =
          transport.request(method, path, body, target: target, timeout: timeout(opts, state))

        state = Fabric.apply(state, result)
        if state.phase == :submitted and state.epoch_id, do: write_journal(opts, state)
        loop(transport, target, state, opts, budget - 1)

      {:replay, _sealed, _digest} ->
        loop(transport, target, Fabric.apply(state, :replay), opts, budget - 1)

      _terminal ->
        state
    end
  end

  # A long-poll request must be allowed to outlive the server-side wait window.
  defp timeout(opts, %Fabric{phase: p, wait_ms: wait}) when p in [:submitted, :leased],
    do: max(Keyword.get(opts, :timeout, 15_000), wait + 5_000)

  defp timeout(opts, _state), do: Keyword.get(opts, :timeout, 15_000)

  defp write_journal(opts, state) do
    path = journal_path(opts, state.request["idempotency_key"])
    File.mkdir_p!(Path.dirname(path))
    tmp = path <> ".tmp"
    File.write!(tmp, Receipt.canonical(Fabric.journal(state)) <> "\n")
    File.rename!(tmp, path)
  end
end
