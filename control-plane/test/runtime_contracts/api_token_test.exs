defmodule ChatGPTCloudControlPlane.RuntimeContracts.ApiTokenTest do
  use ExUnit.Case, async: true
  alias ChatGPTCloudControlPlane.RuntimeContracts.ApiToken
  test "requires token identity and digest" do
    assert :ok = ApiToken.validate(%{token_id: "agent-1", digest: String.duplicate("a", 32)})
    assert {:error, :api_token_identity_missing} = ApiToken.validate(%{token_id: "agent-1"})
  end
end
