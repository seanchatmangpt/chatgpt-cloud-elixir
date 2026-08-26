defmodule ChatGPTCloud.SwarmCoordination.WorkItem do
  @moduledoc """
  Durable work-control record using the SwarmSH JSON coordination vocabulary.

  The row is the concurrency subject. JSON is the portable projection; it does
  not grant execution authority. Consequential DO remains BRCE-gated.
  """

  use Ecto.Schema

  @primary_key {:id, :binary_id, autogenerate: true}
  @foreign_key_type :binary_id

  schema "swarm_work_items" do
    field :work_item_id, :string
    field :source_kind, :string
    field :source_id, :string
    field :work_type, :string
    field :description, :string
    field :priority, :string, default: "medium"
    field :team, :string, default: "chatgpt_swarm"
    field :status, :string, default: "pending"
    field :agent_id, :string
    field :reactor_id, :string, default: "chatgpt_cloud"
    field :estimated_duration, :string, default: "30m"
    field :progress, :integer, default: 0
    field :subject, :map, default: %{}
    field :authority, :map, default: %{}
    field :telemetry, :map, default: %{}
    field :metadata, :map, default: %{}
    field :result, :map, default: %{}
    field :claimed_at, :utc_datetime_usec
    field :last_update, :utc_datetime_usec
    field :completed_at, :utc_datetime_usec

    timestamps(type: :utc_datetime_usec)
  end
end
