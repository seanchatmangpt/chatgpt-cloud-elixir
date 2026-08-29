defmodule ChatGPTCloud.RuntimeIntegration.SecretPolicyTest do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.RuntimeIntegration.SecretPolicy

  test "secret-bearing fields require encryption and receipt redaction" do
    assert SecretPolicy.secret?(:deployment_token)
    assert SecretPolicy.encrypt?(:deployment_token)
    assert SecretPolicy.redact_from_receipt?(:deployment_token)
    refute SecretPolicy.secret?(:run_id)
  end
end
