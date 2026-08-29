defmodule ChatGPTCloudControlPlane.RuntimeContracts.ObanRetryGuardTest do
  use ExUnit.Case, async: true
  alias ChatGPTCloudControlPlane.RuntimeContracts.ObanRetryGuard

  test "unchanged retries are refused" do
    assert :ok = ObanRetryGuard.admit(%{attempt: 1})
    assert {:error, :unchanged_retry_refused} = ObanRetryGuard.admit(%{attempt: 2})
    assert :ok = ObanRetryGuard.admit(%{attempt: 2, changed_hypothesis: true})
  end
end
