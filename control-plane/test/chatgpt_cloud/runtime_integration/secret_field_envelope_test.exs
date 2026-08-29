defmodule ChatGPTCloud.RuntimeIntegration.SecretFieldEnvelopeTest do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.RuntimeIntegration.SecretFieldEnvelope

  test "receipt projection retains encryption metadata without secret reference" do
    envelope = %SecretFieldEnvelope{field: :deployment_token, ciphertext_ref: "vault://cipher/1", key_version: 2}
    assert :ok = SecretFieldEnvelope.admit(envelope)
    assert %{field: :deployment_token, encrypted: true, key_version: 2} = SecretFieldEnvelope.receipt_projection(envelope)
    refute Map.has_key?(SecretFieldEnvelope.receipt_projection(envelope), :ciphertext_ref)
  end
end
