defmodule ChatGPTCloudControlPlane.RuntimeContracts.OcelProtocol do
  @moduledoc "Requires explicit OCEL protocol and schema identity at ingestion boundaries."
  def validate(%{protocol: p, version: v, schema_digest: d}) when is_binary(p) and is_binary(v) and is_binary(d) and byte_size(d) >= 32, do: :ok
  def validate(_), do: {:error, :ocel_protocol_identity_missing}
end
