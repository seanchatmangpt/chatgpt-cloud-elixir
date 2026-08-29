defmodule ChatGPTCloud.RuntimeIntegration.DeploymentGuard do
  @moduledoc "Credential-gated deployment standing. Missing authority can never self-promote to ALIVE."

  @spec admit(String.t() | nil) :: :ok | {:error, {:blocked, :missing_deployment_authority}}
  def admit(token) when is_binary(token) and byte_size(token) > 0, do: :ok
  def admit(_), do: {:error, {:blocked, :missing_deployment_authority}}
end
