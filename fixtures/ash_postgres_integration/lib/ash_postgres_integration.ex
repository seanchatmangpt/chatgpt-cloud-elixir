defmodule AshPostgresIntegration.Ticket do
  use Ash.Resource,
    domain: AshPostgresIntegration.Domain,
    data_layer: AshPostgres.DataLayer

  postgres do
    table "tickets"
    repo AshPostgresIntegration.Repo
  end

  attributes do
    uuid_primary_key :id
    attribute :name, :string, allow_nil?: false, public?: true
    attribute :score, :integer, allow_nil?: false, default: 0, public?: true
  end

  identities do
    identity :unique_name, [:name]
  end

  validations do
    validate compare(:score, greater_than_or_equal_to: 0)
  end

  actions do
    defaults [:read, :destroy, create: [:name, :score], update: [:name, :score]]
  end
end

defmodule AshPostgresIntegration.Domain do
  use Ash.Domain, validate_config_inclusion?: false

  resources do
    resource AshPostgresIntegration.Ticket
  end
end
