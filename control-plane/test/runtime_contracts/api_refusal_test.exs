defmodule ChatGPTCloudControlPlane.RuntimeContracts.ApiRefusalTest do
  use ExUnit.Case, async: true
  alias ChatGPTCloudControlPlane.RuntimeContracts.ApiRefusal
  test "requires code standing and reason" do
    assert :ok = ApiRefusal.validate(%{code: "AUTH_REFUSED", standing: :refused, reason: "outside authority"})
    assert {:error, :invalid_api_refusal} = ApiRefusal.validate(%{code: "AUTH_REFUSED"})
  end
end
