defmodule ChatGPTCloudControlPlane.RuntimeContracts.RuntimeInteropTest do
  use ExUnit.Case, async: true
  alias ChatGPTCloudControlPlane.RuntimeContracts.RuntimeInterop
  test "requires protocol producer and consumer" do
    assert :ok = RuntimeInterop.validate(%{protocol: "ocel", producer: "ex4pm", consumer: "chatgpt-cloud-elixir"})
    assert {:error, :runtime_interop_identity_missing} = RuntimeInterop.validate(%{protocol: "ocel"})
  end
end
