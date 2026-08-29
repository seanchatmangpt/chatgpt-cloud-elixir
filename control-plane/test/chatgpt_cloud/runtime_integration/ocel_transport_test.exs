defmodule ChatGPTCloud.RuntimeIntegration.OcelTransportTest do
  use ExUnit.Case, async: true
  alias ChatGPTCloud.RuntimeIntegration.OcelTransport

  test "accepts only the versioned observational OCEL envelope" do
    assert :ok = OcelTransport.admit(%{"schema" => "chatgpt-cloud-ocel/1", "events" => []})

    assert {:error, :invalid_ocel_envelope} =
             OcelTransport.admit(%{"schema" => "chatgpt-cloud-ocel/2", "events" => []})
  end
end
