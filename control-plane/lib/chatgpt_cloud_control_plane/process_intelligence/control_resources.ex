defmodule ChatGPTCloud.ProcessIntelligence.CostObservation do
  @moduledoc "Metering observation. This records cost evidence; it grants no billing authority."

  use Ash.Resource,
    otp_app: :chatgpt_cloud_control_plane,
    domain: ChatGPTCloud.ProcessIntelligence,
    data_layer: AshPostgres.DataLayer,
    extensions: [AshArchival.Resource, AshJsonApi.Resource, AshGraphql.Resource]

  postgres do
    table "cost_observations"
    repo ChatGPTCloud.Repo
  end

  json_api do
    type "cost_observation"
  end

  graphql do
    type :cost_observation
  end

  actions do
    defaults [:read, :destroy]

    create :create do
      primary? true
      accept [:observation_key, :run_key, :category, :estimated_cost, :basis, :observed_at]
    end
  end

  attributes do
    uuid_primary_key :id
    attribute :observation_key, :string, allow_nil?: false, public?: true
    attribute :run_key, :string, allow_nil?: false, public?: true
    attribute :category, :string, allow_nil?: false, public?: true

    attribute :estimated_cost, AshMoney.Types.Money,
      allow_nil?: false,
      public?: true,
      constraints: [storage_type: :map]

    attribute :basis, :map, allow_nil?: false, default: %{}, public?: true
    attribute :observed_at, :utc_datetime_usec, allow_nil?: false, default: &DateTime.utc_now/0, public?: true
    create_timestamp :inserted_at
    update_timestamp :updated_at
  end

  identities do
    identity :unique_cost_observation, [:observation_key]
  end
end

defmodule ChatGPTCloud.ProcessIntelligence.SecretCredential do
  @moduledoc "Encrypted control-plane credential metadata. Secret material is never an API projection."

  use Ash.Resource,
    otp_app: :chatgpt_cloud_control_plane,
    domain: ChatGPTCloud.ProcessIntelligence,
    data_layer: AshPostgres.DataLayer,
    extensions: [AshCloak, AshArchival.Resource]

  postgres do
    table "secret_credentials"
    repo ChatGPTCloud.Repo
  end

  cloak do
    vault ChatGPTCloud.Vault
    attributes [:secret]
  end

  actions do
    defaults [:read, :destroy]

    create :create do
      primary? true
      accept [:credential_key, :kind, :secret, :digest, :scopes, :active]
    end

    update :rotate do
      accept [:secret, :digest]
    end

    update :disable do
      change set_attribute(:active, false)
    end
  end

  attributes do
    uuid_primary_key :id
    attribute :credential_key, :string, allow_nil?: false, public?: true
    attribute :kind, :string, allow_nil?: false, public?: true
    attribute :secret, :string, allow_nil?: false, sensitive?: true
    attribute :digest, :string, allow_nil?: false, public?: true
    attribute :scopes, {:array, :string}, allow_nil?: false, default: [], public?: true
    attribute :active, :boolean, allow_nil?: false, default: true, public?: true
    create_timestamp :inserted_at
    update_timestamp :updated_at
  end

  identities do
    identity :unique_secret_credential, [:credential_key]
  end
end
