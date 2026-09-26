defmodule ChatGPTCloudControlPlane.RuntimeContracts.GraphqlProjectionGuard do
  @moduledoc "Requires GraphQL mutations to resolve through named Ash actions."

  def admit(%{operation: :query, field: field}) when is_binary(field) and field != "", do: :ok
  def admit(%{operation: :mutation, ash_action: action}) when is_atom(action), do: :ok
  def admit(%{operation: :mutation}), do: {:error, :graphql_mutation_requires_ash_action}
  def admit(_), do: {:error, :invalid_graphql_operation}
end
