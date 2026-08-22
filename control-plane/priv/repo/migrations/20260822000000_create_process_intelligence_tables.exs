defmodule ChatGPTCloud.Repo.Migrations.CreateProcessIntelligenceTables do
  use Ecto.Migration

  def change do
    create table(:ocel_agents, primary_key: false) do
      add :id, :uuid, primary_key: true
      add :agent_key, :text, null: false
      add :first_seen_at, :utc_datetime_usec, null: false
      add :last_seen_at, :utc_datetime_usec, null: false
      add :metadata, :map, null: false, default: %{}
      timestamps(type: :utc_datetime_usec)
    end

    create unique_index(:ocel_agents, [:agent_key])
    create index(:ocel_agents, [:last_seen_at])

    create table(:ocel_runs, primary_key: false) do
      add :id, :uuid, primary_key: true
      add :run_key, :text, null: false
      add :agent_key, :text, null: false
      add :status, :text, null: false
      add :subject_repo, :text
      add :subject_sha, :text
      add :started_at, :utc_datetime_usec, null: false
      add :last_seen_at, :utc_datetime_usec, null: false
      add :ended_at, :utc_datetime_usec
      add :metadata, :map, null: false, default: %{}
      timestamps(type: :utc_datetime_usec)
    end

    create unique_index(:ocel_runs, [:run_key])
    create index(:ocel_runs, [:agent_key])
    create index(:ocel_runs, [:last_seen_at])

    create table(:ocel_events, primary_key: false) do
      add :id, :uuid, primary_key: true
      add :event_key, :text, null: false
      add :agent_key, :text, null: false
      add :run_key, :text, null: false
      add :activity, :text, null: false
      add :lifecycle, :text, null: false
      add :sequence, :bigint, null: false
      add :standing, :text, null: false
      add :authority_domain, :text, null: false
      add :occurred_at, :utc_datetime_usec, null: false
      add :ingested_at, :utc_datetime_usec, null: false
      add :digest, :text, null: false
      add :previous_digest, :text
      add :payload, :map, null: false, default: %{}
      timestamps(type: :utc_datetime_usec)
    end

    create unique_index(:ocel_events, [:event_key])
    create unique_index(:ocel_events, [:run_key, :sequence])
    create index(:ocel_events, [:occurred_at])
    create index(:ocel_events, [:ingested_at])
    create index(:ocel_events, [:agent_key])
    create index(:ocel_events, [:activity])
    create index(:ocel_events, [:standing])

    create table(:ocel_objects, primary_key: false) do
      add :id, :uuid, primary_key: true
      add :object_key, :text, null: false
      add :object_type, :text, null: false
      add :label, :text
      add :attributes, :map, null: false, default: %{}
      add :first_seen_at, :utc_datetime_usec, null: false
      add :last_seen_at, :utc_datetime_usec, null: false
      timestamps(type: :utc_datetime_usec)
    end

    create unique_index(:ocel_objects, [:object_key])
    create index(:ocel_objects, [:object_type])

    create table(:ocel_event_objects, primary_key: false) do
      add :id, :uuid, primary_key: true
      add :event_key, :text, null: false
      add :object_key, :text, null: false
      add :qualifier, :text, null: false
      timestamps(type: :utc_datetime_usec)
    end

    create unique_index(:ocel_event_objects, [:event_key, :object_key, :qualifier])
    create index(:ocel_event_objects, [:object_key])

    create table(:ocel_object_objects, primary_key: false) do
      add :id, :uuid, primary_key: true
      add :source_object_key, :text, null: false
      add :target_object_key, :text, null: false
      add :qualifier, :text, null: false
      timestamps(type: :utc_datetime_usec)
    end

    create unique_index(
             :ocel_object_objects,
             [:source_object_key, :target_object_key, :qualifier],
             name: :ocel_object_objects_identity
           )

    create table(:ocel_receipts, primary_key: false) do
      add :id, :uuid, primary_key: true
      add :receipt_key, :text, null: false
      add :run_key, :text, null: false
      add :standing, :text, null: false
      add :subject_sha, :text
      add :subject_tree_sha, :text
      add :digest, :text, null: false
      add :payload, :map, null: false, default: %{}
      add :observed_at, :utc_datetime_usec, null: false
      timestamps(type: :utc_datetime_usec)
    end

    create unique_index(:ocel_receipts, [:receipt_key])
    create index(:ocel_receipts, [:run_key])
    create index(:ocel_receipts, [:standing])

    create table(:ocel_conformance_results, primary_key: false) do
      add :id, :uuid, primary_key: true
      add :result_key, :text, null: false
      add :run_key, :text, null: false
      add :model_key, :text
      add :fitness, :decimal
      add :standing, :text, null: false
      add :payload, :map, null: false, default: %{}
      add :observed_at, :utc_datetime_usec, null: false
      timestamps(type: :utc_datetime_usec)
    end

    create unique_index(:ocel_conformance_results, [:result_key])
    create index(:ocel_conformance_results, [:run_key])

    create table(:ocel_refusals, primary_key: false) do
      add :id, :uuid, primary_key: true
      add :refusal_key, :text, null: false
      add :run_key, :text, null: false
      add :refusal_type, :text, null: false
      add :reason, :text
      add :payload, :map, null: false, default: %{}
      add :observed_at, :utc_datetime_usec, null: false
      timestamps(type: :utc_datetime_usec)
    end

    create unique_index(:ocel_refusals, [:refusal_key])
    create index(:ocel_refusals, [:run_key])
    create index(:ocel_refusals, [:refusal_type])

    create table(:ocel_process_variants, primary_key: false) do
      add :id, :uuid, primary_key: true
      add :variant_key, :text, null: false
      add :name, :text, null: false
      add :model_type, :text, null: false
      add :model_digest, :text, null: false
      add :payload, :map, null: false, default: %{}
      add :first_seen_at, :utc_datetime_usec, null: false
      add :last_seen_at, :utc_datetime_usec, null: false
      timestamps(type: :utc_datetime_usec)
    end

    create unique_index(:ocel_process_variants, [:variant_key])
    create index(:ocel_process_variants, [:model_digest])
  end
end
