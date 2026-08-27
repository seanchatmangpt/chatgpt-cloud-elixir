defmodule ChatGPTCloudControlPlane.RuntimeContracts.CloakFieldPolicyTest do
  use ExUnit.Case, async: true
  alias ChatGPTCloudControlPlane.RuntimeContracts.CloakFieldPolicy

  test "secret-bearing fields require encryption and receipt exclusion" do
    assert :ok = CloakFieldPolicy.admit(:token, %{encrypted: true, receipt_visible: false})
    assert {:error, {:secret_field_not_cloaked, :token}} = CloakFieldPolicy.admit(:token, %{encrypted: false, receipt_visible: true})
  end
end
