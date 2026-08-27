defmodule ChatGPTCloud.RuntimeIntegration.LifecycleTest do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.RuntimeIntegration.LifecycleGuard

  test "admits declared lifecycle transition and refuses implicit terminal manufacture" do
    assert :ok = LifecycleGuard.admit(:pending, :admitted)
    assert {:error, {:invalid_transition, :pending, :qualified}} =
             LifecycleGuard.admit(:pending, :qualified)
  end
end
