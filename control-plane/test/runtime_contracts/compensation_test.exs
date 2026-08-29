defmodule ChatGPTCloudControlPlane.RuntimeContracts.CompensationTest do
  use ExUnit.Case, async: true
  alias ChatGPTCloudControlPlane.RuntimeContracts.Compensation
  test "requires authority when compensation is required" do
    assert :ok = Compensation.validate(%{required: true, authority_ref: "auth-1"})
    assert {:error, :compensation_authority_missing} = Compensation.validate(%{required: true})
  end
end
