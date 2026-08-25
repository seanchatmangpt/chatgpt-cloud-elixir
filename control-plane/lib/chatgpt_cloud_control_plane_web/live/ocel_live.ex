defmodule ChatGPTCloudWeb.OcelLive do
  use ChatGPTCloudWeb, :live_view

  alias ChatGPTCloud.ProcessIntelligence.Queries

  @topic "process-intelligence:ocel"

  @impl true
  def mount(_params, _session, socket) do
    if connected?(socket) do
      Phoenix.PubSub.subscribe(ChatGPTCloud.PubSub, @topic)
    end

    {:ok,
     socket
     |> assign(:page_title, "Live OCEL")
     |> assign(:stats, safe_stats())
     |> stream(:events, safe_recent_events(), reset: true)}
  end

  @impl true
  def handle_info({:ocel_events, events}, socket) do
    socket =
      Enum.reduce(events, socket, fn event, acc ->
        stream_insert(acc, :events, event, at: 0, limit: 250)
      end)

    {:noreply, assign(socket, :stats, safe_stats())}
  end

  @impl true
  def render(assigns) do
    ~H"""
    <main class="min-h-screen bg-slate-950 text-slate-100">
      <div class="mx-auto max-w-[1600px] px-6 py-8">
        <header class="mb-8 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p class="text-xs font-semibold uppercase tracking-[0.3em] text-cyan-400">ChatGPT Cloud</p>
            <h1 class="mt-2 text-4xl font-semibold tracking-tight">Streaming OCEL Process Intelligence</h1>
            <p class="mt-2 max-w-3xl text-slate-400">
              Exact agent, run, activity, authority, standing, object, and receipt observations streamed from admitted cloud executions.
            </p>
          </div>
          <nav class="flex gap-3 text-sm">
            <a class="rounded-lg border border-slate-700 px-4 py-2 hover:border-cyan-400" href="/admin">AshAdmin</a>
            <a class="rounded-lg border border-slate-700 px-4 py-2 hover:border-cyan-400" href="/healthz">Health</a>
          </nav>
        </header>

        <section class="mb-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
          <.stat label="Events / min" value={@stats.events_last_minute} />
          <.stat label="Active agents" value={@stats.active_agents} />
          <.stat label="Active runs" value={@stats.active_runs} />
          <.stat label="Refusals / hour" value={@stats.refusals_last_hour} />
          <.stat label="Process variants" value={@stats.process_variants} />
        </section>

        <section class="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/70 shadow-2xl">
          <div class="border-b border-slate-800 px-5 py-4">
            <h2 class="font-semibold">Live event stream</h2>
            <p class="text-sm text-slate-400">Newest admitted observations appear first. Duplicate event identities are ignored.</p>
          </div>

          <div class="grid grid-cols-[minmax(150px,0.8fr)_minmax(130px,0.7fr)_minmax(180px,1.2fr)_minmax(130px,0.7fr)_minmax(120px,0.6fr)_minmax(160px,1fr)] gap-3 border-b border-slate-800 bg-slate-950/50 px-5 py-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
            <div>Time</div>
            <div>Agent</div>
            <div>Activity</div>
            <div>Lifecycle</div>
            <div>Standing</div>
            <div>Run</div>
          </div>

          <div id="ocel-events" phx-update="stream" class="max-h-[68vh] overflow-y-auto">
            <div
              :for={{dom_id, event} <- @streams.events}
              id={dom_id}
              class="grid grid-cols-[minmax(150px,0.8fr)_minmax(130px,0.7fr)_minmax(180px,1.2fr)_minmax(130px,0.7fr)_minmax(120px,0.6fr)_minmax(160px,1fr)] gap-3 border-b border-slate-800/70 px-5 py-3 text-sm hover:bg-slate-800/40"
            >
              <div class="font-mono text-xs text-slate-400">{timestamp(event.occurred_at)}</div>
              <div class="truncate font-mono text-xs text-cyan-300">{event.agent_key}</div>
              <div class="truncate font-medium">{event.activity}</div>
              <div class="truncate text-slate-300">{event.lifecycle}</div>
              <div><span class={standing_class(event.standing)}>{event.standing}</span></div>
              <div class="truncate font-mono text-xs text-slate-400">{event.run_key}</div>
            </div>
          </div>
        </section>
      </div>
    </main>
    """
  end

  defp stat(assigns) do
    ~H"""
    <div class="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
      <div class="text-xs font-semibold uppercase tracking-wider text-slate-500">{@label}</div>
      <div class="mt-2 text-3xl font-semibold tabular-nums">{@value}</div>
    </div>
    """
  end

  defp standing_class("ALIVE"),
    do: "rounded-full bg-emerald-500/15 px-2 py-1 text-xs font-semibold text-emerald-300"

  defp standing_class("BLOCKED"),
    do: "rounded-full bg-amber-500/15 px-2 py-1 text-xs font-semibold text-amber-300"

  defp standing_class("BUILD_BROKEN"),
    do: "rounded-full bg-red-500/15 px-2 py-1 text-xs font-semibold text-red-300"

  defp standing_class("REFUSED_" <> _),
    do: "rounded-full bg-fuchsia-500/15 px-2 py-1 text-xs font-semibold text-fuchsia-300"

  defp standing_class(_),
    do: "rounded-full bg-slate-700 px-2 py-1 text-xs font-semibold text-slate-200"

  defp timestamp(%DateTime{} = value), do: DateTime.to_iso8601(value)
  defp timestamp(%NaiveDateTime{} = value), do: NaiveDateTime.to_iso8601(value)
  defp timestamp(value), do: to_string(value)

  defp safe_recent_events do
    Queries.recent_events()
  rescue
    _ -> []
  end

  defp safe_stats do
    Queries.stats()
  rescue
    _ ->
      %{events_last_minute: 0, active_agents: 0, active_runs: 0, refusals_last_hour: 0, process_variants: 0}
  end
end
