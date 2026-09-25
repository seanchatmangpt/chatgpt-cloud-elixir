defmodule ChatGPTCloud.Xaas.Fabric do
  @moduledoc """
  Pure client state machine for the XaaS bounded runtime fabric
  (`/internal-api/fabric`, protocol `xaas-fabric/1`):

      new -> probed -> admitted -> submitted -> leased -> sealed -> replayed

  `next/1` names the one request (or local replay) the state needs; `apply/2`
  folds the observed result in. No I/O happens here; `ChatGPTCloud.Xaas.Runner`
  is the only impure loop. Terminal phases: `:replayed`, `{:blocked, reason}`,
  `{:refused, reason}`, `{:unsupported, reason}`, `{:broken, reason}`.

  `classify/2` mirrors Python `classify_http` in `scripts/xaas-runtime.py`.
  `resume/1` covers a client crash between submit and its response: the same
  idempotency key is resubmitted and the server must return the same epoch.
  """

  alias ChatGPTCloud.Xaas.{Capabilities, Receipt}

  @protocol "xaas-fabric/1"
  @base "/internal-api/fabric"
  @key ~r/^[A-Za-z0-9._:-]{1,128}$/
  @default_wait_ms 25_000

  defstruct phase: :new,
            request: %{},
            run_id: nil,
            epoch_id: nil,
            expected_epoch_id: nil,
            replay?: false,
            resumed?: false,
            cursor: nil,
            sealed: nil,
            declared_digest: nil,
            polls: 0,
            wait_ms: @default_wait_ms,
            outcome: nil,
            trace: []

  @type phase ::
          :new
          | :probed
          | :admitted
          | :submitted
          | :leased
          | :sealed
          | :replayed
          | {:blocked, String.t()}
          | {:refused, String.t()}
          | {:unsupported, String.t()}
          | {:broken, String.t()}

  @type t :: %__MODULE__{}

  def protocol, do: @protocol

  @doc """
  Start a fabric run. `request` needs `"goal"` and `"idempotency_key"`; optional
  `"exact_subject"`, `"worktree"`, `"verifier_suite"`. Provider is always `"zcode"`.
  """
  @spec new(map(), keyword()) :: t()
  def new(request, opts \\ []) do
    request = Map.new(request, fn {k, v} -> {to_string(k), v} end)
    wait_ms = min(Keyword.get(opts, :wait_ms, @default_wait_ms), @default_wait_ms)
    state = %__MODULE__{request: Map.put(request, "provider", "zcode"), wait_ms: wait_ms}

    cond do
      not non_empty?(request["goal"]) ->
        terminal(state, {:refused, "GOAL_REQUIRED"}, "REFUSED_REQUEST")

      not (is_binary(request["idempotency_key"]) and
               Regex.match?(@key, request["idempotency_key"])) ->
        terminal(state, {:refused, "IDEMPOTENCY_KEY_INVALID"}, "REFUSED_REQUEST")

      true ->
        state
    end
  end

  @doc "The next action required by `state`."
  @spec next(t()) ::
          {:request, :get | :post, String.t(), map() | nil}
          | {:replay, map(), String.t()}
          | {:done, map()}
          | {:blocked, String.t()}
          | {:refused, String.t()}
          | {:unsupported, String.t()}
          | {:broken, String.t()}
  def next(%__MODULE__{phase: :new}), do: {:request, :get, @base <> "/probe", nil}

  def next(%__MODULE__{phase: :probed}),
    do: {:request, :post, @base <> "/admit", %{"capabilities" => Capabilities.allowlist()}}

  def next(%__MODULE__{phase: :admitted, request: req}),
    do: {:request, :post, @base <> "/runs", req}

  def next(%__MODULE__{phase: p} = s) when p in [:submitted, :leased],
    do: {:request, :get, receipts_path(s), nil}

  def next(%__MODULE__{phase: :sealed, sealed: sealed, declared_digest: d}),
    do: {:replay, sealed, d}

  def next(%__MODULE__{phase: :replayed, sealed: sealed}), do: {:done, sealed}
  def next(%__MODULE__{phase: {kind, reason}}), do: {kind, reason}

  @doc "Path of the bounded long-poll for sealed receipts."
  def receipts_path(%__MODULE__{epoch_id: id, wait_ms: wait, cursor: cursor}) do
    query = URI.encode_query(Enum.reject([wait_ms: wait, after: cursor], &is_nil(elem(&1, 1))))
    "#{@base}/epochs/#{URI.encode(id, &URI.char_unreserved?/1)}/receipts?#{query}"
  end

  @doc "Terminal predicate."
  def terminal?(%__MODULE__{phase: p}),
    do: p == :replayed or match?({_, _}, p)

  @doc """
  Fold an observation into the state: a transport result for a `{:request, ...}`
  step, or `:replay` for the local replay step.
  """
  @spec apply(t(), {:ok, pos_integer(), term()} | {:error, term()} | :replay) :: t()
  def apply(%__MODULE__{phase: :sealed} = s, :replay) do
    case Receipt.verify_replay(s.sealed, s.declared_digest) do
      :ok ->
        s
        |> step("replay", nil, "ALIVE", nil)
        |> Map.merge(%{phase: :replayed, outcome: {"ALIVE", nil}})

      {:refused, :replay_digest_mismatch} ->
        s
        |> step("replay", nil, "REFUSED", "replay_digest_mismatch")
        |> terminal({:refused, "replay_digest_mismatch"}, "REFUSED")
    end
  end

  def apply(%__MODULE__{} = s, {:error, _} = err) do
    {standing, reason} = classify(0, err)

    s
    |> step(step_name(s), nil, standing, reason)
    |> terminal(phase_for(standing, reason), standing)
  end

  def apply(%__MODULE__{} = s, {:ok, status, body}) do
    case classify(status, nil) do
      {"ALIVE", nil} ->
        alive(s, status, body)

      {standing, reason} ->
        reason = refine_reason(status, body, reason)

        s
        |> step(step_name(s), status, standing, reason)
        |> terminal(phase_for(standing, reason), standing)
    end
  end

  # --- ALIVE transitions ---------------------------------------------------

  defp alive(%__MODULE__{phase: :new} = s, status, body) do
    caps = if is_map(body), do: body["capabilities"], else: nil

    if is_map(body) and body["protocol"] == @protocol and is_list(caps) and
         Enum.sort(caps) == Enum.sort(Capabilities.allowlist()) do
      wait = min(s.wait_ms, int_or(body["long_poll_max_ms"], @default_wait_ms))
      s |> step("probe", status, "ALIVE", nil) |> Map.merge(%{phase: :probed, wait_ms: wait})
    else
      s
      |> step("probe", status, "UNSUPPORTED", "CONTRACT_MISMATCH")
      |> terminal({:unsupported, "CONTRACT_MISMATCH"}, "UNSUPPORTED")
    end
  end

  defp alive(%__MODULE__{phase: :probed} = s, status, body) do
    admitted =
      if is_map(body) and is_list(body["admitted"]), do: Enum.sort(body["admitted"]), else: nil

    if admitted == Enum.sort(Capabilities.allowlist()) do
      s |> step("admit", status, "ALIVE", nil) |> Map.put(:phase, :admitted)
    else
      s
      |> step("admit", status, "REFUSED_AUTHORITY", "CAPABILITY_NOT_ADMITTED")
      |> terminal({:refused, "CAPABILITY_NOT_ADMITTED"}, "REFUSED_AUTHORITY")
    end
  end

  defp alive(%__MODULE__{phase: :admitted} = s, status, body) do
    with true <- is_map(body),
         run_id when is_binary(run_id) <- body["run_id"],
         epoch_id when is_binary(epoch_id) <- body["epoch_id"] do
      if s.expected_epoch_id && s.expected_epoch_id != epoch_id do
        s
        |> step("submit", status, "REFUSED", "IDEMPOTENCY_VIOLATION")
        |> terminal({:refused, "IDEMPOTENCY_VIOLATION"}, "REFUSED")
      else
        s
        |> step("submit", status, "ALIVE", if(body["replay"] == true, do: "IDEMPOTENT_REPLAY"))
        |> Map.merge(%{
          phase: :submitted,
          run_id: run_id,
          epoch_id: epoch_id,
          replay?: body["replay"] == true
        })
      end
    else
      _ ->
        s
        |> step("submit", status, "BUILD_BROKEN", "PROTOCOL_SHAPE")
        |> terminal({:broken, "PROTOCOL_SHAPE"}, "BUILD_BROKEN")
    end
  end

  defp alive(%__MODULE__{phase: p} = s, 204, _body) when p in [:submitted, :leased] do
    s |> step("receipts", 204, "ALIVE", "LONG_POLL_TIMEOUT") |> Map.update!(:polls, &(&1 + 1))
  end

  defp alive(%__MODULE__{phase: p} = s, status, body) when p in [:submitted, :leased] do
    receipts = if is_map(body) and is_list(body["receipts"]), do: body["receipts"], else: nil

    case receipts do
      [%{"receipt" => sealed, "digest" => digest} | _]
      when is_map(sealed) and is_binary(digest) ->
        s
        |> step("receipts", status, "ALIVE", "SEALED")
        |> Map.merge(%{
          phase: :sealed,
          sealed: sealed,
          declared_digest: digest,
          cursor: digest,
          polls: s.polls + 1
        })

      [] ->
        phase = if body["state"] == "leased", do: :leased, else: p

        s
        |> step("receipts", status, "ALIVE", if(phase == :leased, do: "LEASED"))
        |> Map.merge(%{phase: phase, cursor: body["cursor"] || s.cursor, polls: s.polls + 1})

      _ ->
        s
        |> step("receipts", status, "BUILD_BROKEN", "PROTOCOL_SHAPE")
        |> terminal({:broken, "PROTOCOL_SHAPE"}, "BUILD_BROKEN")
    end
  end

  defp alive(s, status, _body) do
    s
    |> step(step_name(s), status, "BUILD_BROKEN", "ILLEGAL_TRANSITION")
    |> terminal({:broken, "ILLEGAL_TRANSITION"}, "BUILD_BROKEN")
  end

  # --- classification (Python classify_http parity) -----------------------

  @doc """
  `{standing, reason}` for an HTTP status or transport error; identical table to
  Python `classify_http(status, transport_error)`.
  """
  @spec classify(non_neg_integer(), nil | {:error, {atom(), term()}}) ::
          {String.t(), String.t() | nil}
  def classify(_status, {:error, {:network, _}}), do: {"BLOCKED", "NETWORK"}
  def classify(_status, {:error, {:config, _}}), do: {"BLOCKED", "IRREDUCIBLE_TRANSPORT_CONFIG"}
  def classify(_status, {:error, {:redirect, _}}), do: {"BLOCKED", "REDIRECT_REFUSED"}
  def classify(_status, {:error, _}), do: {"BUILD_BROKEN", "PROTOCOL"}
  def classify(status, nil) when status in 200..299, do: {"ALIVE", nil}
  def classify(401, nil), do: {"REFUSED_AUTHENTICATION", "AUTHENTICATION"}
  def classify(403, nil), do: {"REFUSED_AUTHORITY", "AUTHORITY"}
  def classify(429, nil), do: {"BLOCKED", "CAPACITY"}
  def classify(503, nil), do: {"BLOCKED", "SERVER_MISCONFIGURED"}
  def classify(404, nil), do: {"BLOCKED", "NOT_FOUND_OR_NOT_VISIBLE"}
  def classify(status, nil) when status in 400..499, do: {"REFUSED_REQUEST", "HTTP_#{status}"}
  def classify(status, nil), do: {"BLOCKED", "HTTP_#{status}"}

  # --- crash window ---------------------------------------------------------

  @doc "Durable journal of a state (written before submit and after its response)."
  @spec journal(t()) :: map()
  def journal(%__MODULE__{} = s) do
    %{
      "schema" => "chatgpt-cloud.xaas-fabric-journal/1",
      "request" => s.request,
      "run_id" => s.run_id,
      "epoch_id" => s.epoch_id,
      "phase" => phase_name(s.phase)
    }
  end

  @doc """
  Rebuild a state from a journal after a client crash. The run is re-probed,
  re-admitted and resubmitted with the same idempotency key; if the journal already
  holds an epoch id, the server must return that same epoch.
  """
  @spec resume(map(), keyword()) :: t()
  def resume(%{"request" => request} = journal, opts \\ []) do
    %{new(request, opts) | resumed?: true, expected_epoch_id: journal["epoch_id"]}
  end

  # --- receipt --------------------------------------------------------------

  @doc "Client receipt for a (usually terminal) state; BRCE fields included."
  @spec receipt(t(), map()) :: map()
  def receipt(%__MODULE__{} = s, extra \\ %{}) do
    {standing, reason} =
      case s.outcome do
        nil when s.phase in [:submitted, :leased] -> {"PARTIAL_ALIVE", "AWAITING_SEAL"}
        nil -> {"BLOCKED", "STEP_BUDGET_EXHAUSTED"}
        other -> other
      end

    Receipt.build(
      Map.merge(
        %{
          "identity" => %{
            "idempotency_key" => s.request["idempotency_key"],
            "request_sha256" => Receipt.digest(s.request),
            "run_id" => s.run_id,
            "epoch_id" => s.epoch_id,
            "sealed_receipt_sha256" => s.declared_digest
          },
          "consequence" => %{
            "phase" => phase_name(s.phase),
            "idempotent_replay" => s.replay?,
            "resumed" => s.resumed?,
            "polls" => s.polls,
            "trace" => Enum.reverse(s.trace)
          },
          "sealed_receipt" => s.sealed,
          "standing" => standing,
          "reason" => reason,
          "replay" =>
            "cd xaas-runtime/elixir && mix xaas_runtime.fabric --goal <goal> --idempotency-key " <>
              to_string(s.request["idempotency_key"])
        },
        extra
      )
    )
  end

  # --- helpers --------------------------------------------------------------

  defp terminal(s, phase, standing) do
    {_, reason} = phase
    %{s | phase: phase, outcome: {standing, reason}}
  end

  defp phase_for("BLOCKED", r), do: {:blocked, r}
  defp phase_for("UNSUPPORTED", r), do: {:unsupported, r}
  defp phase_for("BUILD_BROKEN", r), do: {:broken, r}
  defp phase_for("REFUSED" <> _, r), do: {:refused, r}

  defp refine_reason(403, %{"reason" => r}, _default) when is_binary(r) and r != "", do: r
  defp refine_reason(_status, _body, default), do: default

  defp step(s, name, status, standing, reason) do
    entry = %{"step" => name, "http_status" => status, "standing" => standing, "reason" => reason}
    %{s | trace: [entry | s.trace]}
  end

  defp step_name(%__MODULE__{phase: :new}), do: "probe"
  defp step_name(%__MODULE__{phase: :probed}), do: "admit"
  defp step_name(%__MODULE__{phase: :admitted}), do: "submit"
  defp step_name(%__MODULE__{phase: p}) when p in [:submitted, :leased], do: "receipts"
  defp step_name(_), do: "terminal"

  defp phase_name({kind, reason}), do: "#{kind}:#{reason}"
  defp phase_name(p), do: Atom.to_string(p)

  defp int_or(v, _default) when is_integer(v) and v > 0, do: v
  defp int_or(_, default), do: default

  defp non_empty?(v), do: is_binary(v) and String.trim(v) != ""
end
