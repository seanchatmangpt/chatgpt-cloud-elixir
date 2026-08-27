defmodule ChatGPTCloud.RuntimeIntegration.IdempotencyTest do
  use ExUnit.Case, async: true
  alias ChatGPTCloud.RuntimeIntegration.Idempotency

  test "same semantic input produces the same replay key regardless of map insertion order" do
    left = Idempotency.key("qualify", %{run: "r1", subject: "s1"})
    right = Idempotency.key("qualify", Map.new([subject: "s1", run: "r1"]))
    assert left == right
  end
end
