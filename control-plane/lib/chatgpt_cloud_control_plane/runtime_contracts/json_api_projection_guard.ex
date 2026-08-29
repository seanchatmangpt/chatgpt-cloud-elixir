defmodule ChatGPTCloudControlPlane.RuntimeContracts.JsonApiProjectionGuard do
  @moduledoc "Separates JSON:API projection from mutation authority."

  def admit(%{mode: :read, resource: resource}) when is_binary(resource) and resource != "", do: :ok
  def admit(%{mode: :write, authority: :ash_action, resource: resource}) when is_binary(resource) and resource != "", do: :ok
  def admit(%{mode: :write}), do: {:error, :json_api_write_requires_ash_action}
  def admit(_), do: {:error, :invalid_json_api_projection}
end
