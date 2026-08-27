defmodule ChatGPTCloud.RuntimeIntegration.EnvironmentObservation do
  @moduledoc "Non-actuating observation of runtime/toolchain/service availability."
  @enforce_keys [:platform, :architecture]
  defstruct [:platform, :architecture, :otp, :elixir, services: %{}, network: :unknown]

  @spec supports?(struct(), atom()) :: boolean()
  def supports?(%__MODULE__{services: services}, service), do: Map.get(services, service, false) == true
end
