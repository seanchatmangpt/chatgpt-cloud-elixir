defmodule AshPhoenixSmoke.Contact do
  use Ash.Resource,
    domain: AshPhoenixSmoke.Domain,
    data_layer: Ash.DataLayer.Ets

  attributes do
    uuid_primary_key :id
    attribute :name, :string, allow_nil?: false, public?: true
    attribute :email, :string, allow_nil?: false, public?: true
  end

  identities do
    identity :unique_email, [:email], pre_check_with: AshPhoenixSmoke.Domain
  end

  validations do
    validate match(:email, ~r/^[^\s@]+@[^\s@]+\.[^\s@]+$/), message: "must be a valid email"
  end

  actions do
    defaults [:read, :destroy, create: [:name, :email], update: [:name, :email]]
  end
end

defmodule AshPhoenixSmoke.Domain do
  use Ash.Domain, validate_config_inclusion?: false

  resources do
    resource AshPhoenixSmoke.Contact
  end
end
