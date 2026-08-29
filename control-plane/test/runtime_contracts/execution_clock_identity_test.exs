defmodule ChatGPTCloudControlPlane.RuntimeContracts.ExecutionClockIdentityTest do
  use ExUnit.Case, async: true
  alias ChatGPTCloudControlPlane.RuntimeContracts.ExecutionClockIdentity

  test "requires explicit clock and observation time" do
    assert :ok = ExecutionClockIdentity.validate(%{clock: :system, observed_at: DateTime.utc_now()})
    assert {:error, :invalid_execution_clock_identity} = ExecutionClockIdentity.validate(%{clock: :system})
  end
end
