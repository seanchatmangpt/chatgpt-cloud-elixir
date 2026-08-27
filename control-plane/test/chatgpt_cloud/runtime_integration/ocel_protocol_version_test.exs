defmodule ChatGPTCloud.RuntimeIntegration.OcelProtocolVersionTest do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.RuntimeIntegration.OcelProtocolVersion

  test "v1 is explicit and unknown versions are refused" do
    assert OcelProtocolVersion.supported?("v1")
    assert :ok = OcelProtocolVersion.admit("v1")
    assert {:error, :unsupported_ocel_protocol} = OcelProtocolVersion.admit("v2")
  end
end
