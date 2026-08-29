defmodule ChatGPTCloud.RuntimeIntegration.CostAuthority do
  @moduledoc "Prevents metering evidence from acquiring billing authority."

  @spec admit(map()) :: :ok | {:error, :billing_authority_forbidden}
  def admit(%{billing_authority: true}), do: {:error, :billing_authority_forbidden}
  def admit(_), do: :ok
end
