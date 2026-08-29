defmodule ChatGPTCloudControlPlane.RuntimeContracts.RuntimeRateLimitTest do
  use ExUnit.Case, async: true
  alias ChatGPTCloudControlPlane.RuntimeContracts.RuntimeRateLimit

  test "requires positive finite rate limits" do
    assert :ok = RuntimeRateLimit.validate(%{limit: 10, interval_ms: 1_000})
    assert {:error, :invalid_runtime_rate_limit} = RuntimeRateLimit.validate(%{limit: 0, interval_ms: 1_000})
  end
end
