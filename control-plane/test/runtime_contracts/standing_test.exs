defmodule ChatGPTCloudControlPlane.RuntimeContracts.StandingTest do
  use ExUnit.Case, async: true
  alias ChatGPTCloudControlPlane.RuntimeContracts.Standing
  test "accepts evidence vocabulary only" do
    assert :ok = Standing.validate(:alive)
    assert {:error, {:invalid_standing, :done}} = Standing.validate(:done)
  end
end
