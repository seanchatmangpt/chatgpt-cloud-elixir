defmodule ChatGPTCloud.RuntimeIntegration.RuntimeErrorTest do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.RuntimeIntegration.RuntimeError

  test "normalizes errors into typed runtime evidence" do
    error = RuntimeError.new(:dependency_unavailable, %{dependency: :postgres})
    assert error.kind == :dependency_unavailable
    assert error.details == %{dependency: :postgres}
    assert RuntimeError.standing(error) == :build_broken
  end
end
