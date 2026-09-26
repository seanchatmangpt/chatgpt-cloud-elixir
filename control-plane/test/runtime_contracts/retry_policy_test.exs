defmodule ChatGPTCloudControlPlane.RuntimeContracts.RetryPolicyTest do
  use ExUnit.Case, async: true
  alias ChatGPTCloudControlPlane.RuntimeContracts.RetryPolicy
  test "bounds attempts and delay" do
    assert :ok = RetryPolicy.validate(%{max_attempts: 5, backoff_ms: 1000})
    assert {:error, :invalid_retry_policy} = RetryPolicy.validate(%{max_attempts: 99, backoff_ms: 0})
  end
end
