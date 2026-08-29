defmodule ChatGPTCloud.RuntimeIntegration.ReceiptIdentityTest do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.RuntimeIntegration.ReceiptIdentity

  test "same subject command and environment yield same receipt identity" do
    subject = String.duplicate("e", 40)
    left = ReceiptIdentity.digest(subject, "mix test", "otp-29")
    right = ReceiptIdentity.digest(subject, "mix test", "otp-29")
    assert left == right
    assert byte_size(left) == 64
    refute left == ReceiptIdentity.digest(subject, "mix test", "otp-28")
  end
end
