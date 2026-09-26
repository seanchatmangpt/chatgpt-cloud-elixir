defmodule ChatGPTCloudControlPlane.RuntimeContracts.CloakedSecretTest do
  use ExUnit.Case, async: true
  alias ChatGPTCloudControlPlane.RuntimeContracts.CloakedSecret
  test "requires encrypted secret storage" do
    assert :ok = CloakedSecret.validate(%{encrypted: true, ciphertext: "cipher"})
    assert {:error, :plaintext_secret_refused} = CloakedSecret.validate(%{encrypted: false, ciphertext: "plain"})
  end
end
