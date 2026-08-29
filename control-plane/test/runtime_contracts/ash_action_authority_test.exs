defmodule ChatGPTCloudControlPlane.RuntimeContracts.AshActionAuthorityTest do
  use ExUnit.Case, async: true
  alias ChatGPTCloudControlPlane.RuntimeContracts.AshActionAuthority

  test "DO requires BRCE while select and construct remain non-actuating" do
    assert :ok = AshActionAuthority.admit(%{phase: :select})
    assert :ok = AshActionAuthority.admit(%{phase: :construct})
    assert {:error, :ash_action_do_requires_brce} = AshActionAuthority.admit(%{phase: :do})
  end
end
