defmodule ChatGPTCloud.ProcessIntelligence.SwarmAgent do
  @moduledoc """
  A swarmsh-style coordination agent's live state.

  Ported from `vendors/swarmsh`'s `agent_status.json` records and
  `vendors/swarmsh-v2`'s `AgentState`/`AgentStatus`
  (`vendors/swarmsh-v2/src/coordination.rs:63-97`). This resource tracks
  live agent state only (capacity, heartbeat, current claim); the
  claim/complete/heartbeat *events* belong on the existing OCEL pipeline
  (`ChatGPTCloud.ProcessIntelligence.Event`) using the
  `swarmsh.agent.*`/`swarmsh.work.*` activity vocabulary from
  `vendors/swarmsh-v2/semantic-conventions/*.yaml` — this resource is not a
  duplicate event log.
  """

  use Ash.Resource,
    otp_app: :chatgpt_cloud_control_plane,
    domain: ChatGPTCloud.ProcessIntelligence,
    data_layer: AshPostgres.DataLayer,
    extensions: [AshStateMachine]

  postgres do
    table "swarm_agents"
    repo ChatGPTCloud.Repo
  end

  state_machine do
    initial_states [:idle]
    default_initial_state :idle

    transitions do
      transition :start_work, from: [:idle, :active], to: :working
      transition :become_active, from: [:idle, :working], to: :active
      transition :go_idle, from: [:working, :active], to: :idle
      transition :block, from: [:idle, :working, :active], to: :blocked
      transition :fail, from: [:idle, :working, :active, :blocked], to: :failed
      transition :recover, from: [:blocked, :failed], to: :idle
    end
  end

  actions do
    defaults [:read, :destroy]

    create :register do
      primary? true

      accept [
        :agent_key,
        :team_key,
        :role,
        :specialization,
        :capacity
      ]

      change set_attribute(:last_heartbeat_at, &DateTime.utc_now/0)
    end

    update :heartbeat do
      change set_attribute(:last_heartbeat_at, &DateTime.utc_now/0)
    end

    update :start_work do
      accept [:current_work_key]
      require_atomic? false
      change transition_state(:working)
      change set_attribute(:last_heartbeat_at, &DateTime.utc_now/0)
    end

    update :become_active do
      require_atomic? false
      change transition_state(:active)
      change set_attribute(:last_heartbeat_at, &DateTime.utc_now/0)
    end

    update :go_idle do
      require_atomic? false
      change transition_state(:idle)
      change set_attribute(:current_work_key, nil)
      change set_attribute(:last_heartbeat_at, &DateTime.utc_now/0)
    end

    update :block do
      require_atomic? false
      change transition_state(:blocked)
    end

    update :fail do
      require_atomic? false
      change transition_state(:failed)
    end

    update :recover do
      require_atomic? false
      change transition_state(:idle)
      change set_attribute(:current_work_key, nil)
    end

    update :update_metrics do
      accept [:performance_metrics]
    end
  end

  attributes do
    uuid_primary_key :id
    attribute :agent_key, :string, allow_nil?: false, public?: true
    attribute :team_key, :string, public?: true
    attribute :role, :string, public?: true
    attribute :specialization, :string, public?: true
    attribute :capacity, :float, default: 1.0, public?: true
    attribute :current_work_key, :string, public?: true
    attribute :last_heartbeat_at, :utc_datetime_usec, public?: true
    attribute :performance_metrics, :map, default: %{}, public?: true
    create_timestamp :inserted_at
    update_timestamp :updated_at
  end

  identities do
    identity :unique_agent_key, [:agent_key]
  end
end
