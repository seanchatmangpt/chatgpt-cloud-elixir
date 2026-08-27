defmodule ChatGPTCloud.RuntimeIntegration.ApiProjectionContract do
  @moduledoc """Shared declaration for generated JSON:API and GraphQL machine projections."""

  @enforce_keys [:surface, :resource, :operations]
  defstruct [:surface, :resource, :operations]

  @surfaces [:json_api, :graphql]
  @mutations [:create, :update, :destroy]

  @spec valid?(t()) :: boolean() when t: %__MODULE__{}
  def valid?(%__MODULE__{surface: surface, resource: resource, operations: operations}) do
    surface in @surfaces and is_atom(resource) and is_list(operations) and
      Enum.all?(operations, &(&1 in [:read, :list | @mutations]))
  end

  @spec mutation?(atom()) :: boolean()
  def mutation?(operation), do: operation in @mutations
end
