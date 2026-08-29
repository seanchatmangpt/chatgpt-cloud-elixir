defmodule ChatGPTCloud.ProcessIntelligence.SwarmTeam do
  @moduledoc """
  A swarmsh-style coordination team.

  Ported from `vendors/swarmsh`'s free-text `team` field on work claims and
  agent-status records (no structured team schema exists upstream — this is
  deliberately minimal: identity + a velocity aggregate, replacing swarmsh's
  append-only `velocity_log.txt`). See the swarmsh -> Ash conversion plan for
  the full rationale.
  """

  use Ash.Resource,
    otp_app: :chatgpt_cloud_control_plane,
    domain: ChatGPTCloud.ProcessIntelligence,
    data_layer: AshPostgres.DataLayer

  postgres do
    table "swarm_teams"
    repo ChatGPTCloud.Repo
  end

  actions do
    defaults [:read, :destroy]

    create :create do
      primary? true
      accept [:team_key, :name]
    end

    update :update do
      primary? true
      accept [:name]
    end
  end

  attributes do
    uuid_primary_key :id
    attribute :team_key, :string, allow_nil?: false, public?: true
    attribute :name, :string, public?: true
    create_timestamp :inserted_at
    update_timestamp :updated_at
  end

  aggregates do
    count :completed_work_item_count, :completed_work_items
    sum :velocity, :completed_work_items, :priority
  end

  relationships do
    has_many :completed_work_items, ChatGPTCloud.ProcessIntelligence.SwarmWorkItem do
      no_attributes? true
      filter expr(team_key == parent(team_key) and state == :completed)
    end
  end

  identities do
    identity :unique_team_key, [:team_key]
  end
end
