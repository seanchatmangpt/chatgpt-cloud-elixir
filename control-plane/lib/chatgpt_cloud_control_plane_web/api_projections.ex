defmodule ChatGPTCloudWeb.JsonApiRouter do
  @moduledoc false

  use AshJsonApi.Router,
    domains: [ChatGPTCloud.ProcessIntelligence],
    open_api: "/open-api",
    json_schema: "/json-schema",
    prefix: "/api/json"
end

defmodule ChatGPTCloudWeb.GraphqlSchema do
  @moduledoc """
  `AshMoney.Types.Money` declares its Absinthe field types as `:money`/
  `:money_input` (see `AshMoney.Types.Money.graphql_type/1` and
  `graphql_input_type/1`) but ash_money itself does not define those Absinthe
  types -- consuming apps must. `CostObservation.estimated_cost` is the only
  attribute using this type, so it's defined here, shaped to match
  `AshMoney.Types.Money.dump_to_embedded/2`'s JSON-Schema-documented output
  (`amount` as a decimal string, `currency` as a string currency code).
  """
  use Absinthe.Schema
  use AshGraphql, domains: [ChatGPTCloud.ProcessIntelligence]

  object :money do
    field :amount, :string
    field :currency, :string
  end

  input_object :money_input do
    field :amount, :string
    field :currency, :string
  end

  query do
  end
end
