defmodule ChatGPTCloud.RuntimeIntegration.JobKindTest do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.RuntimeIntegration.JobKind

  test "admits only durable runtime job classes" do
    assert JobKind.valid?(:qualification)
    assert JobKind.valid?(:replay)
    assert JobKind.valid?(:mining)
    refute JobKind.valid?(:deploy)
  end
end
