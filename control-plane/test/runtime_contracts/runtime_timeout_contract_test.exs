defmodule ChatGPTCloudControlPlane.RuntimeContracts.RuntimeTimeoutContractTest do
  use ExUnit.Case, async: true
  alias ChatGPTCloudControlPlane.RuntimeContracts.RuntimeTimeoutContract

  test "requires positive bounded timeout" do
    assert :ok = RuntimeTimeoutContract.validate(%{timeout_ms: 30_000})
    assert {:error, {:invalid_runtime_timeout, 0}} = RuntimeTimeoutContract.validate(%{timeout_ms: 0})
  end
end
