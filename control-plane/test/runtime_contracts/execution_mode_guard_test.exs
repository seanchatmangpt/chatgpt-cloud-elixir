defmodule ChatGPTCloudControlPlane.RuntimeContracts.ExecutionModeGuardTest do
  use ExUnit.Case, async: true
  alias ChatGPTCloudControlPlane.RuntimeContracts.ExecutionModeGuard

  test "replay and construct cannot acquire fresh DO" do
    assert :ok = ExecutionModeGuard.admit(%{mode: :replay, fresh_do: false})
    assert {:error, {:fresh_do_refused, :construct}} = ExecutionModeGuard.admit(%{mode: :construct, fresh_do: true})
    assert :ok = ExecutionModeGuard.admit(%{mode: :do, authority: :brce})
  end
end
