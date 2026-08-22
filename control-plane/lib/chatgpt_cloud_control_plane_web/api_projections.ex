defmodule ChatGPTCloudWeb.JsonApiRouter do
  @moduledoc false

  use AshJsonApi.Router,
    domains: [ChatGPTCloud.ProcessIntelligence],
    open_api: "/open-api",
    json_schema: "/json-schema",
    prefix: "/api/json"
end

defmodule ChatGPTCloudWeb.GraphqlSchema do
  @moduledoc false
  use Absinthe.Schema
  use AshGraphql, domains: [ChatGPTCloud.ProcessIntelligence]

  query do
  end
end
