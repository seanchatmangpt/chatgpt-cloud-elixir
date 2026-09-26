defmodule ChatGPTCloudControlPlane.RuntimeContracts.JsonApiProjection do
  @moduledoc "Constrains JSON:API projections to declared resources and actions."

  def validate(resource, action, allowed) when is_atom(resource) and is_atom(action) and is_map(allowed) do
    if action in Map.get(allowed, resource, []), do: :ok, else: {:error, :json_api_action_not_exposed}
  end

  def validate(_, _, _), do: {:error, :invalid_json_api_projection}
end
