defmodule ChatGPTCloud.SwarmCoordination.Receipt do
  @moduledoc "Append-only receipt for a work-control transition."

  use Ecto.Schema

  @primary_key {:id, :binary_id, autogenerate: true}
  @foreign_key_type :binary_id

  schema "swarm_work_receipts" do
    field :receipt_id, :string
    field :work_item_id, :string
    field :event_type, :string
    field :agent_id, :string
    field :trace_id, :string
    field :standing, :string
    field :digest, :string
    field :payload, :map, default: %{}
    field :occurred_at, :utc_datetime_usec

    timestamps(type: :utc_datetime_usec, updated_at: false)
  end
end
