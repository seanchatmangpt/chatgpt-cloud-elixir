defmodule ChatGPTCloud.RuntimeIntegration.SecretReceiptFilterTest do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.RuntimeIntegration.SecretReceiptFilter

  test "redacts nested secret keys while preserving non-secret evidence" do
    value = %{run_id: "r1", nested: %{api_token: "secret", count: 2}, entries: [%{password: "p"}]}
    redacted = SecretReceiptFilter.redact(value)
    assert redacted.run_id == "r1"
    assert redacted.nested.api_token == "[REDACTED]"
    assert redacted.nested.count == 2
    assert hd(redacted.entries).password == "[REDACTED]"
  end
end
