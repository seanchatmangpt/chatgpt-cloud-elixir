defmodule ChatGPTCloudControlPlane.RuntimeContracts.AshActionTest do
  use ExUnit.Case, async: true
  alias ChatGPTCloudControlPlane.RuntimeContracts.AshAction
  test "requires resource action subject and authority" do
    assert :ok = AshAction.validate(%{resource: :run, action: :ingest, subject: %{sha: "abc"}, authority_ref: "auth-1"})
    assert {:error, :ash_action_contract_incomplete} = AshAction.validate(%{resource: :run, action: :ingest})
  end
end
