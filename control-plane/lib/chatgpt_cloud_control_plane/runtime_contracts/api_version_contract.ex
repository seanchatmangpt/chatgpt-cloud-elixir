defmodule ChatGPTCloudControlPlane.RuntimeContracts.ApiVersionContract do
  @moduledoc "Requires machine-facing runtime APIs to declare an explicit supported version."

  @supported ["v1", "2026-08-27"]

  def admit(version) when version in @supported, do: :ok
  def admit(version) when is_binary(version), do: {:error, {:unsupported_api_version, version}}
  def admit(_), do: {:error, :invalid_api_version}
end
