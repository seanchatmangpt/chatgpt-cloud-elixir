defmodule ChatGPTCloud.RuntimeIntegration.OcelIngestionContractTest do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.RuntimeIntegration.OcelIngestionContract

  test "versioned OCEL transport remains observational" do
    assert :ok = OcelIngestionContract.admit(%OcelIngestionContract{protocol_version: "v1", producer: "ex4pm", event_id: "evt-1"})
    assert {:error, :transport_actuation_refused} = OcelIngestionContract.admit(%OcelIngestionContract{protocol_version: "v1", producer: "ex4pm", event_id: "evt-1", authority: :do})
  end
end
