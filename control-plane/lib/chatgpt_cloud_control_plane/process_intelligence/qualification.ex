defmodule ChatGPTCloud.ProcessIntelligence.Qualification do
  @moduledoc """
  Internal qualification control record.

  OCEL runs are observations from external producers. A qualification is the
  control-plane decision process that evaluates those observations. Keeping the
  two separate prevents an observed producer status from silently becoming
  control-plane standing.
  """

  use Ash.Resource,
    otp_app: :chatgpt_cloud_control_plane,
    domain: ChatGPTCloud.ProcessIntelligence,
    data_layer: AshPostgres.DataLayer,
    extensions: [
      AshStateMachine,
      AshOban,
      AshArchival.Resource,
      AshJsonApi.Resource,
      AshGraphql.Resource
    ]

  postgres do
    table "qualifications"
    repo ChatGPTCloud.Repo
  end

  json_api do
    type "qualification"
  end

  graphql do
    type :qualification
  end

  state_machine do
    initial_states [:pending]
    default_initial_state :pending

    transitions do
      transition :start, from: [:pending, :retrying], to: :running
      transition :qualify, from: :running, to: :qualified
      transition :degrade, from: :running, to: :degraded
      transition :block, from: [:pending, :running, :retrying], to: :blocked
      transition :fail, from: [:running, :retrying], to: :failed
      transition :retry, from: [:degraded, :blocked, :failed], to: :retrying
    end
  end

  oban do
    scheduled_actions do
      schedule :reconcile_pending, "* * * * *",
        action: :reconcile_pending,
        queue: :qualification,
        max_attempts: 3,
        worker_module_name: ChatGPTCloud.ProcessIntelligence.Workers.ReconcilePending
    end
  end

  actions do
    defaults [:read, :destroy]

    create :create do
      primary? true

      accept [
        :qualification_key,
        :run_key,
        :subject_repo,
        :subject_sha,
        :kind,
        :standing,
        :result,
        :requested_at
      ]
    end

    update :start do
      change transition_state(:running)
      change set_attribute(:started_at, &DateTime.utc_now/0)
    end

    update :qualify do
      accept [:standing, :result]
      change transition_state(:qualified)
      change set_attribute(:completed_at, &DateTime.utc_now/0)
    end

    update :degrade do
      accept [:standing, :result]
      change transition_state(:degraded)
      change set_attribute(:completed_at, &DateTime.utc_now/0)
    end

    update :block do
      accept [:standing, :result]
      change transition_state(:blocked)
      change set_attribute(:completed_at, &DateTime.utc_now/0)
    end

    update :fail do
      accept [:standing, :result]
      change transition_state(:failed)
      change set_attribute(:completed_at, &DateTime.utc_now/0)
    end

    update :retry do
      change transition_state(:retrying)
      change set_attribute(:completed_at, nil)
    end

    action :reconcile_pending, :integer do
      run fn _input, _context ->
        {:ok, ChatGPTCloud.ProcessIntelligence.QualificationReconciler.reconcile_pending()}
      end
    end
  end

  attributes do
    uuid_primary_key :id
    attribute :qualification_key, :string, allow_nil?: false, public?: true
    attribute :run_key, :string, allow_nil?: false, public?: true
    attribute :subject_repo, :string, public?: true
    attribute :subject_sha, :string, public?: true
    attribute :kind, :string, allow_nil?: false, default: "process_intelligence", public?: true
    attribute :standing, :string, allow_nil?: false, default: "UNKNOWN", public?: true
    attribute :result, :map, allow_nil?: false, default: %{}, public?: true
    attribute :requested_at, :utc_datetime_usec, allow_nil?: false, default: &DateTime.utc_now/0, public?: true
    attribute :started_at, :utc_datetime_usec, public?: true
    attribute :completed_at, :utc_datetime_usec, public?: true
    create_timestamp :inserted_at
    update_timestamp :updated_at
  end

  identities do
    identity :unique_qualification_key, [:qualification_key]
  end
end
