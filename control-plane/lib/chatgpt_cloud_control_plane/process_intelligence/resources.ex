defmodule ChatGPTCloud.ProcessIntelligence.ResourceHelpers do
  @moduledoc false

  defmacro __using__(table) do
    quote bind_quoted: [table: table] do
      use Ash.Resource,
        otp_app: :chatgpt_cloud_control_plane,
        domain: ChatGPTCloud.ProcessIntelligence,
        data_layer: AshPostgres.DataLayer

      postgres do
        table table
        repo ChatGPTCloud.Repo
      end

      actions do
        defaults [:read]
      end
    end
  end
end

defmodule ChatGPTCloud.ProcessIntelligence.Agent do
  use ChatGPTCloud.ProcessIntelligence.ResourceHelpers, "ocel_agents"

  attributes do
    uuid_primary_key :id
    attribute :agent_key, :string, allow_nil?: false, public?: true
    attribute :first_seen_at, :utc_datetime_usec, allow_nil?: false, public?: true
    attribute :last_seen_at, :utc_datetime_usec, allow_nil?: false, public?: true
    attribute :metadata, :map, default: %{}, public?: true
  end

  identities do
    identity :unique_agent_key, [:agent_key]
  end
end

defmodule ChatGPTCloud.ProcessIntelligence.Run do
  use ChatGPTCloud.ProcessIntelligence.ResourceHelpers, "ocel_runs"

  attributes do
    uuid_primary_key :id
    attribute :run_key, :string, allow_nil?: false, public?: true
    attribute :agent_key, :string, allow_nil?: false, public?: true
    attribute :status, :string, allow_nil?: false, public?: true
    attribute :subject_repo, :string, public?: true
    attribute :subject_sha, :string, public?: true
    attribute :started_at, :utc_datetime_usec, allow_nil?: false, public?: true
    attribute :last_seen_at, :utc_datetime_usec, allow_nil?: false, public?: true
    attribute :ended_at, :utc_datetime_usec, public?: true
    attribute :metadata, :map, default: %{}, public?: true
  end

  identities do
    identity :unique_run_key, [:run_key]
  end
end

defmodule ChatGPTCloud.ProcessIntelligence.Event do
  use ChatGPTCloud.ProcessIntelligence.ResourceHelpers, "ocel_events"

  attributes do
    uuid_primary_key :id
    attribute :event_key, :string, allow_nil?: false, public?: true
    attribute :agent_key, :string, allow_nil?: false, public?: true
    attribute :run_key, :string, allow_nil?: false, public?: true
    attribute :activity, :string, allow_nil?: false, public?: true
    attribute :lifecycle, :string, allow_nil?: false, public?: true
    attribute :sequence, :integer, allow_nil?: false, public?: true
    attribute :standing, :string, allow_nil?: false, public?: true
    attribute :authority_domain, :string, allow_nil?: false, public?: true
    attribute :occurred_at, :utc_datetime_usec, allow_nil?: false, public?: true
    attribute :ingested_at, :utc_datetime_usec, allow_nil?: false, public?: true
    attribute :digest, :string, allow_nil?: false, public?: true
    attribute :previous_digest, :string, public?: true
    attribute :payload, :map, default: %{}, public?: true
  end

  identities do
    identity :unique_event_key, [:event_key]
    identity :unique_run_sequence, [:run_key, :sequence]
  end
end

defmodule ChatGPTCloud.ProcessIntelligence.Object do
  use ChatGPTCloud.ProcessIntelligence.ResourceHelpers, "ocel_objects"

  attributes do
    uuid_primary_key :id
    attribute :object_key, :string, allow_nil?: false, public?: true
    attribute :object_type, :string, allow_nil?: false, public?: true
    attribute :label, :string, public?: true
    attribute :attributes, :map, default: %{}, public?: true
    attribute :first_seen_at, :utc_datetime_usec, allow_nil?: false, public?: true
    attribute :last_seen_at, :utc_datetime_usec, allow_nil?: false, public?: true
  end

  identities do
    identity :unique_object_key, [:object_key]
  end
end

defmodule ChatGPTCloud.ProcessIntelligence.EventObject do
  use ChatGPTCloud.ProcessIntelligence.ResourceHelpers, "ocel_event_objects"

  attributes do
    uuid_primary_key :id
    attribute :event_key, :string, allow_nil?: false, public?: true
    attribute :object_key, :string, allow_nil?: false, public?: true
    attribute :qualifier, :string, allow_nil?: false, public?: true
  end

  identities do
    identity :unique_event_object, [:event_key, :object_key, :qualifier]
  end
end

defmodule ChatGPTCloud.ProcessIntelligence.ObjectObject do
  use ChatGPTCloud.ProcessIntelligence.ResourceHelpers, "ocel_object_objects"

  attributes do
    uuid_primary_key :id
    attribute :source_object_key, :string, allow_nil?: false, public?: true
    attribute :target_object_key, :string, allow_nil?: false, public?: true
    attribute :qualifier, :string, allow_nil?: false, public?: true
  end

  identities do
    identity :unique_object_object, [:source_object_key, :target_object_key, :qualifier]
  end
end

defmodule ChatGPTCloud.ProcessIntelligence.Receipt do
  use ChatGPTCloud.ProcessIntelligence.ResourceHelpers, "ocel_receipts"

  attributes do
    uuid_primary_key :id
    attribute :receipt_key, :string, allow_nil?: false, public?: true
    attribute :run_key, :string, allow_nil?: false, public?: true
    attribute :standing, :string, allow_nil?: false, public?: true
    attribute :subject_sha, :string, public?: true
    attribute :subject_tree_sha, :string, public?: true
    attribute :digest, :string, allow_nil?: false, public?: true
    attribute :payload, :map, default: %{}, public?: true
    attribute :observed_at, :utc_datetime_usec, allow_nil?: false, public?: true
  end

  identities do
    identity :unique_receipt_key, [:receipt_key]
  end
end

defmodule ChatGPTCloud.ProcessIntelligence.ConformanceResult do
  use ChatGPTCloud.ProcessIntelligence.ResourceHelpers, "ocel_conformance_results"

  attributes do
    uuid_primary_key :id
    attribute :result_key, :string, allow_nil?: false, public?: true
    attribute :run_key, :string, allow_nil?: false, public?: true
    attribute :model_key, :string, public?: true
    attribute :fitness, :decimal, public?: true
    attribute :standing, :string, allow_nil?: false, public?: true
    attribute :payload, :map, default: %{}, public?: true
    attribute :observed_at, :utc_datetime_usec, allow_nil?: false, public?: true
  end

  identities do
    identity :unique_conformance_result, [:result_key]
  end
end

defmodule ChatGPTCloud.ProcessIntelligence.Refusal do
  use ChatGPTCloud.ProcessIntelligence.ResourceHelpers, "ocel_refusals"

  attributes do
    uuid_primary_key :id
    attribute :refusal_key, :string, allow_nil?: false, public?: true
    attribute :run_key, :string, allow_nil?: false, public?: true
    attribute :refusal_type, :string, allow_nil?: false, public?: true
    attribute :reason, :string, public?: true
    attribute :payload, :map, default: %{}, public?: true
    attribute :observed_at, :utc_datetime_usec, allow_nil?: false, public?: true
  end

  identities do
    identity :unique_refusal, [:refusal_key]
  end
end

defmodule ChatGPTCloud.ProcessIntelligence.ProcessVariant do
  use ChatGPTCloud.ProcessIntelligence.ResourceHelpers, "ocel_process_variants"

  attributes do
    uuid_primary_key :id
    attribute :variant_key, :string, allow_nil?: false, public?: true
    attribute :name, :string, allow_nil?: false, public?: true
    attribute :model_type, :string, allow_nil?: false, public?: true
    attribute :model_digest, :string, allow_nil?: false, public?: true
    attribute :payload, :map, default: %{}, public?: true
    attribute :first_seen_at, :utc_datetime_usec, allow_nil?: false, public?: true
    attribute :last_seen_at, :utc_datetime_usec, allow_nil?: false, public?: true
  end

  identities do
    identity :unique_process_variant, [:variant_key]
  end
end
