defmodule ChatGPTCloud.RuntimeIntegration.ApiProjectionContract do
  @moduledoc """Shared declaration for generated JSON:API and GraphQL machine projections."""

  @enforce_keys [:surface, :resource, :operations]
  defstruct [:surface, :resource, :operations]

  @type t :: %__MODULE__{surface: :json_api | :graphql, resource: atom(), operations: [atom()]}

  @surfaces [:json_api, :graphql]
  @mutations [:create, :update, :destroy]

  @spec valid?(t()) :: boolean()
  def valid?(%__MODULE__{surface: surface, resource: resource, operations: operations}) do
    surface in @surfaces and is_atom(resource) and is_list(operations) and
      Enum.all?(operations, &(&1 in [:read, :list | @mutations]))
  end

  @spec mutation?(atom()) :: boolean()
  def mutation?(operation), do: operation in @mutations
end
