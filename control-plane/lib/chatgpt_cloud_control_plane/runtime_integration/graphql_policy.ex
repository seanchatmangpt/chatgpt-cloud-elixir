defmodule ChatGPTCloud.RuntimeIntegration.GraphqlPolicy do
  @moduledoc "Bounds GraphQL exposure to explicitly declared query actions."

  @spec query?(atom(), [atom()]) :: boolean()
  def query?(action, declared_queries), do: action in declared_queries
end
