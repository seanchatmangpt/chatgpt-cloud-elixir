defmodule ChatGPTCloud.ProcessIntelligence.SwarmWorkItem do
  @moduledoc """
  A swarmsh-style unit of claimable work.

  Ported from `vendors/swarmsh`'s `work_claims.json` records
  (`coordination_helper.sh:198-335`) and `vendors/swarmsh-v2`'s
  `Work`/`WorkState` (`src/coordination.rs:110-123`).

  The upstream shell implementation guarantees exactly-once claims with a
  `noclobber` lock file plus a whole-file read/rewrite/atomic-rename. That
  mechanism is a workaround for JSON-file storage; it is deliberately not
  ported. What's ported is the *guarantee* it exists to provide (exactly
  one agent claims a given work item), expressed here as an
  `Ash.Resource.Change.Builtins.optimistic_lock/1` on `:version`: the
  `:claim` action's UPDATE is compiled with `WHERE version = <value read>`,
  so of N concurrent claimants only the first commits — the rest affect
  zero rows and Ash raises `Ash.Error.Changes.StaleRecord`. Postgres's own
  transactional isolation replaces the file lock.

  (AshStateMachine's own fully-atomic `UPDATE ... WHERE status = ...`
  compilation isn't usable here — this Ash/AshPostgres combination can't
  push the state-machine's "no matching transition" error into a query
  expression — so state transitions run non-atomically, and the
  `optimistic_lock` change is what actually carries the concurrency
  guarantee.)
  """

  use Ash.Resource,
    otp_app: :chatgpt_cloud_control_plane,
    domain: ChatGPTCloud.ProcessIntelligence,
    data_layer: AshPostgres.DataLayer,
    extensions: [AshStateMachine]

  postgres do
    table "swarm_work_items"
    repo ChatGPTCloud.Repo
  end

  state_machine do
    initial_states [:pending]
    default_initial_state :pending

    transitions do
      transition :claim, from: :pending, to: :active
      transition :complete, from: :active, to: :completed
      transition :fail, from: :active, to: :failed
      transition :abandon, from: [:pending, :active], to: :abandoned
      transition :requeue, from: [:active, :abandoned], to: :pending
    end
  end

  actions do
    defaults [:read, :destroy]

    create :create do
      primary? true

      accept [
        :work_item_id,
        :work_type,
        :priority,
        :description,
        :estimated_duration_secs,
        :team_key
      ]
    end

    update :claim do
      accept [:claimed_by_agent_key]
      require_atomic? false

      change transition_state(:active)
      change set_attribute(:claimed_at, &DateTime.utc_now/0)
      change increment(:attempt_count)
      # The exactly-once-claim guarantee: compiles to
      # `UPDATE ... SET version = version + 1 WHERE version = <read value>`.
      change optimistic_lock(:version)
    end

    update :complete do
      require_atomic? false
      change transition_state(:completed)
    end

    update :fail do
      require_atomic? false
      change transition_state(:failed)
    end

    update :abandon do
      require_atomic? false
      change transition_state(:abandoned)
      change set_attribute(:claimed_by_agent_key, nil)
    end

    update :requeue do
      require_atomic? false
      change transition_state(:pending)
      change set_attribute(:claimed_by_agent_key, nil)
      change set_attribute(:claimed_at, nil)
    end
  end

  attributes do
    uuid_primary_key :id
    attribute :work_item_id, :string, allow_nil?: false, public?: true
    attribute :work_type, :string, public?: true
    attribute :priority, :integer, default: 50, public?: true
    attribute :description, :string, public?: true
    attribute :estimated_duration_secs, :integer, public?: true
    attribute :team_key, :string, public?: true
    attribute :claimed_by_agent_key, :string, public?: true
    attribute :claimed_at, :utc_datetime_usec, public?: true
    attribute :attempt_count, :integer, default: 0, public?: true
    attribute :version, :integer, default: 0, public?: true
    create_timestamp :inserted_at
    update_timestamp :updated_at
  end

  identities do
    identity :unique_work_item_id, [:work_item_id]
  end
end
