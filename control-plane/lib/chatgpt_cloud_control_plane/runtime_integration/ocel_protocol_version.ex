defmodule ChatGPTCloud.RuntimeIntegration.OcelProtocolVersion do
  @moduledoc """Supported version set for the observational OCEL ingestion protocol."""

  @supported ["v1"]

  @spec supported?(String.t()) :: boolean()
  def supported?(version), do: version in @supported

  @spec admit(String.t()) :: :ok | {:error, :unsupported_ocel_protocol}
  def admit(version), do: if(supported?(version), do: :ok, else: {:error, :unsupported_ocel_protocol})

  @spec supported() :: [String.t()]
  def supported, do: @supported
end
