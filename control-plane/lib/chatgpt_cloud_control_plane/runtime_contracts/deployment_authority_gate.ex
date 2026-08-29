defmodule ChatGPTCloudControlPlane.RuntimeContracts.DeploymentAuthorityGate do
  @moduledoc "Keeps deployment credential-gated; missing authority is BLOCKED rather than executable."

  def admit(%{target: target, authority: :granted}) when is_binary(target) and target != "", do: :ok
  def admit(%{target: target}) when is_binary(target) and target != "", do: {:error, {:blocked_deployment_authority, target}}
  def admit(_), do: {:error, :invalid_deployment_request}
end
