defmodule ChatGPTCloud.Repo.Migrations.CreateSwarmCoordinationTables do
  use Ecto.Migration

  def change do
    create table(:swarm_work_items, primary_key: false) do
      add :id, :uuid, primary_key: true
      add :work_item_id, :text, null: false
      add :source_kind, :text
      add :source_id, :text
      add :work_type, :text, null: false
      add :description, :text, null: false, default: ""
      add :priority, :text, null: false, default: "medium"
      add :team, :text, null: false, default: "chatgpt_swarm"
      add :status, :text, null: false, default: "pending"
      add :agent_id, :text
      add :reactor_id, :text, null: false, default: "chatgpt_cloud"
      add :estimated_duration, :text, null: false, default: "30m"
      add :progress, :integer, null: false, default: 0
      add :subject, :map, null: false, default: %{}
      add :authority, :map, null: false, default: %{}
      add :telemetry, :map, null: false, default: %{}
      add :metadata, :map, null: false, default: %{}
      add :result, :map, null: false, default: %{}
      add :claimed_at, :utc_datetime_usec
      add :last_update, :utc_datetime_usec
      add :completed_at, :utc_datetime_usec
      timestamps(type: :utc_datetime_usec)
    end

    create unique_index(:swarm_work_items, [:work_item_id])
    create index(:swarm_work_items, [:status, :priority])
    create index(:swarm_work_items, [:agent_id, :status])
    create index(:swarm_work_items, [:source_kind, :source_id])

    create constraint(:swarm_work_items, :swarm_work_progress_range,
             check: "progress >= 0 AND progress <= 100"
           )

    create constraint(:swarm_work_items, :swarm_work_status_values,
             check:
               "status IN ('pending','active','in_progress','completed','blocked','refused')"
           )

    create table(:swarm_work_receipts, primary_key: false) do
      add :id, :uuid, primary_key: true
      add :receipt_id, :text, null: false
      add :work_item_id, :text, null: false
      add :event_type, :text, null: false
      add :agent_id, :text
      add :trace_id, :text
      add :standing, :text, null: false
      add :digest, :text, null: false
      add :payload, :map, null: false, default: %{}
      add :occurred_at, :utc_datetime_usec, null: false
      timestamps(type: :utc_datetime_usec, updated_at: false)
    end

    create unique_index(:swarm_work_receipts, [:receipt_id])
    create index(:swarm_work_receipts, [:work_item_id, :occurred_at])
    create index(:swarm_work_receipts, [:trace_id])
  end
end
