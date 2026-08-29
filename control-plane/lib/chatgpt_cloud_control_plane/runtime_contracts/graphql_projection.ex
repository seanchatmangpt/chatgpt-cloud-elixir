defmodule ChatGPTCloudControlPlane.RuntimeContracts.GraphqlProjection do
  @moduledoc "Constrains GraphQL fields to bounded read/query capabilities."

  def validate(field, allowed_fields) when is_atom(field) and is_list(allowed_fields) do
    if field in allowed_fields, do: :ok, else: {:error, :graphql_field_not_exposed}
  end

  def validate(_, _), do: {:error, :invalid_graphql_projection}
end
