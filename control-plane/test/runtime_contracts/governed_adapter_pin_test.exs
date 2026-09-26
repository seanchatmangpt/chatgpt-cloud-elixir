defmodule ChatGPTCloudControlPlane.RuntimeContracts.GovernedAdapterPinTest do
  use ExUnit.Case, async: true
  alias ChatGPTCloudControlPlane.RuntimeContracts.GovernedAdapterPin

  test "pins the exact reusable marketplace primitive" do
    identity = GovernedAdapterPin.identity()
    assert :ok = GovernedAdapterPin.validate(identity)
    assert {:error, :governed_runtime_adapter_pin_mismatch} = GovernedAdapterPin.validate(Map.put(identity, :sha, "drift"))
  end
end
