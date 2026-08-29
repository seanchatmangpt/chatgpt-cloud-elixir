defmodule ChatGPTCloudControlPlane.RuntimeContracts.OcelProtocolTest do
  use ExUnit.Case, async: true
  alias ChatGPTCloudControlPlane.RuntimeContracts.OcelProtocol
  test "requires protocol version and schema digest" do
    assert :ok = OcelProtocol.validate(%{protocol: "ocel", version: "2.0", schema_digest: String.duplicate("s", 32)})
    assert {:error, :ocel_protocol_identity_missing} = OcelProtocol.validate(%{protocol: "ocel"})
  end
end
