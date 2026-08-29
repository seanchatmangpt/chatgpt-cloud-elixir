defmodule ChatGPTCloudControlPlane.RuntimeContracts.IngestionProtocolVersion do
  @moduledoc "Admits only explicit versioned ingestion protocols; observational transport cannot self-upgrade."

  @supported ["ocel/2.0", "ggen/ecosystem/ocel/current"]

  def admit(version) when version in @supported, do: :ok
  def admit(version) when is_binary(version), do: {:error, {:unsupported_ingestion_protocol, version}}
  def admit(_), do: {:error, :invalid_ingestion_protocol}
end
