defmodule ChatGPTCloudWeb.HumanValueLive do
  use ChatGPTCloudWeb, :live_view

  alias ChatGPTCloud.HumanValue.{Provider, World}

  @impl true
  def mount(_params, _session, socket) do
    run_id =
      System.get_env("HUMAN_VALUE_RUN_ID") ||
        "hv-runtime-#{System.system_time(:microsecond)}"

    worlds = read_worlds(run_id)

    {:ok,
     socket
     |> assign(:page_title, "Human Value Runtime")
     |> assign(:run_id, run_id)
     |> assign(:worlds, worlds)
     |> assign(:latest_receipt, receipt_json(List.first(worlds), "read"))}
  end

  @impl true
  def handle_event("acquire", _params, socket) do
    seed = Provider.next_seed()
    attrs = Provider.acquire(socket.assigns.run_id, seed)

    world =
      World
      |> Ash.Changeset.for_create(:acquire, attrs)
      |> Ash.create!()
      |> Ash.load!([:revenue_from_customer_cents, :revenue_for_customer_cents])

    worlds = [world | socket.assigns.worlds]

    {:noreply,
     socket
     |> assign(:worlds, worlds)
     |> assign(:latest_receipt, receipt_json(world, "acquire"))}
  end

  @impl true
  def handle_event("qualify", %{"id" => id}, socket) do
    world = Enum.find(socket.assigns.worlds, &(&1.id == id))

    qualified =
      world
      |> Ash.Changeset.for_update(:qualify, %{
        status: :qualified,
        qualified_at: DateTime.utc_now()
      })
      |> Ash.update!()
      |> Ash.load!([:revenue_from_customer_cents, :revenue_for_customer_cents])

    worlds = Enum.map(socket.assigns.worlds, &if(&1.id == qualified.id, do: qualified, else: &1))

    {:noreply,
     socket
     |> assign(:worlds, worlds)
     |> assign(:latest_receipt, receipt_json(qualified, "qualify"))}
  end

  @impl true
  def render(assigns) do
    ~H"""
    <main class="min-h-screen bg-slate-950 text-slate-100" data-human-value-run={@run_id}>
      <div class="mx-auto max-w-6xl px-6 py-10">
        <header class="mb-8">
          <p class="text-xs font-semibold uppercase tracking-[0.3em] text-emerald-400">
            Human-perceived value court
          </p>
          <h1 class="mt-2 text-4xl font-semibold">Dynamic Ash value world</h1>
          <p class="mt-3 max-w-3xl text-slate-400">
            Every nonconstant business value on this surface is acquired during this runtime, owned by Ash, and rendered with provenance. Synthetic economic values prove software behavior only.
          </p>
          <div class="mt-4 font-mono text-xs text-slate-500" data-testid="run-id">{@run_id}</div>
        </header>

        <section class="mb-8 flex flex-wrap items-center gap-3">
          <button
            id="acquire-world"
            phx-click="acquire"
            class="rounded-xl bg-emerald-400 px-5 py-3 font-semibold text-slate-950 hover:bg-emerald-300"
          >
            Acquire synthetic value world
          </button>
          <span class="text-sm text-slate-400" data-testid="world-count">
            {length(@worlds)} runtime worlds
          </span>
        </section>

        <section id="human-value-worlds" class="grid gap-5">
          <article
            :for={world <- @worlds}
            id={"world-#{world.id}"}
            data-world
            data-scenario-id={world.scenario_id}
            data-seed={world.seed}
            data-provider={world.provider}
            data-ash-resource="ChatGPTCloud.HumanValue.World"
            data-ash-action={if world.status == :qualified, do: "qualify", else: "acquire"}
            class="rounded-2xl border border-slate-800 bg-slate-900/70 p-6"
          >
            <div class="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
              <div>
                <p class="font-mono text-xs text-cyan-300" data-field="scenario-id">
                  {world.scenario_id}
                </p>
                <h2 class="mt-1 text-2xl font-semibold" data-field="organization">
                  {world.organization}
                </h2>
                <p class="text-slate-400" data-field="opportunity">{world.opportunity}</p>
              </div>
              <div class="flex items-center gap-3">
                <span
                  class="rounded-full bg-slate-800 px-3 py-1 text-xs font-semibold uppercase"
                  data-field="status"
                >
                  {world.status}
                </span>
                <button
                  :if={world.status == :acquired}
                  phx-click="qualify"
                  phx-value-id={world.id}
                  class="rounded-lg border border-emerald-500/50 px-3 py-2 text-sm text-emerald-300"
                  data-testid="qualify-world"
                >
                  Qualify
                </button>
              </div>
            </div>

            <div class="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <.value_card label="Offer" value={money(world.offer_cents, world.currency)} field="offer" />
              <.value_card label="Invoice" value={money(world.invoice_cents, world.currency)} field="invoice" />
              <.value_card label="Revenue FROM customer" value={money(world.revenue_from_customer_cents, world.currency)} field="revenue-from" />
              <.value_card label="Revenue FOR customer" value={money(world.revenue_for_customer_cents, world.currency)} field="revenue-for" />
            </div>

            <dl class="mt-6 grid gap-x-6 gap-y-2 text-sm sm:grid-cols-2 lg:grid-cols-3">
              <div><dt class="text-slate-500">Contact</dt><dd data-field="contact">{world.contact_name} · {world.contact_email}</dd></div>
              <div><dt class="text-slate-500">Provider</dt><dd class="font-mono text-xs" data-field="provider">{world.provider}</dd></div>
              <div><dt class="text-slate-500">Seed</dt><dd class="font-mono" data-field="seed">{world.seed}</dd></div>
              <div><dt class="text-slate-500">Acquired</dt><dd class="font-mono text-xs" data-field="acquired-at">{DateTime.to_iso8601(world.acquired_at)}</dd></div>
              <div><dt class="text-slate-500">Ash record</dt><dd class="font-mono text-xs" data-field="ash-record">{world.id}</dd></div>
              <div><dt class="text-slate-500">Evidence class</dt><dd data-field="evidence-class">SYNTHETIC</dd></div>
            </dl>
          </article>
        </section>

        <section class="mt-8 rounded-2xl border border-slate-800 bg-slate-950 p-5">
          <h2 class="text-sm font-semibold uppercase tracking-wider text-slate-400">Latest value receipt</h2>
          <pre id="human-value-receipt" data-testid="value-receipt" class="mt-3 overflow-x-auto whitespace-pre-wrap text-xs text-cyan-200"><%= @latest_receipt %></pre>
        </section>
      </div>
    </main>
    """
  end

  defp value_card(assigns) do
    ~H"""
    <div class="rounded-xl border border-slate-800 bg-slate-950/70 p-4">
      <div class="text-xs uppercase tracking-wider text-slate-500">{@label}</div>
      <div class="mt-2 text-xl font-semibold tabular-nums" data-field={@field}>{@value}</div>
    </div>
    """
  end

  defp read_worlds(run_id) do
    World
    |> Ash.read!()
    |> Enum.filter(&(&1.run_id == run_id))
    |> Enum.sort_by(&DateTime.to_unix(&1.acquired_at, :microsecond), :desc)
    |> Ash.load!([:revenue_from_customer_cents, :revenue_for_customer_cents])
  end

  defp money(cents, currency) do
    major = div(cents, 100)
    minor = rem(cents, 100)
    "#{currency} #{major}.#{minor |> Integer.to_string() |> String.pad_leading(2, "0")}"
  end

  defp receipt_json(nil, _action), do: Jason.encode!(%{standing: "HUMAN_VALUE_UNKNOWN"})

  defp receipt_json(world, action) do
    Jason.encode!(%{
      schema: "human-value-receipt/v1",
      scenario_id: world.scenario_id,
      run_id: world.run_id,
      provider: world.provider,
      seed: world.seed,
      ash_resource: "ChatGPTCloud.HumanValue.World",
      ash_action: action,
      ash_record_id: world.id,
      phoenix_route: "/human-value",
      live_view: "ChatGPTCloudWeb.HumanValueLive",
      rendered_values: %{
        organization: world.organization,
        opportunity: world.opportunity,
        revenue_from_customer_cents: world.revenue_from_customer_cents,
        revenue_for_customer_cents: world.revenue_for_customer_cents,
        status: world.status
      },
      acquired_at: world.acquired_at,
      synthetic: world.synthetic,
      standing: "VALUE_PARTIAL_PENDING_PLAYWRIGHT"
    })
  end
end
