defmodule ChatGPTCloudControlPlane.RuntimeContracts.IdempotencyKeyTest do
  use ExUnit.Case, async: true
  alias ChatGPTCloudControlPlane.RuntimeContracts.IdempotencyKey
  test "requires stable key strength" do
    assert :ok = IdempotencyKey.validate("0123456789abcdef")
    assert {:error, :missing_or_weak_idempotency_key} = IdempotencyKey.validate("short")
  end
end
