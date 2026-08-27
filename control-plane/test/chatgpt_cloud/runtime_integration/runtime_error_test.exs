defmodule ChatGPTCloud.RuntimeIntegration.RuntimeErrorTest do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.RuntimeIntegration.RuntimeError

  test "preserves typed build-broken reason and details" do
    error = RuntimeError.new(:build_broken, :dependency_unavailable, %{dependency: :postgres})
    assert error.type == :build_broken
    assert error.reason == :dependency_unavailable
    assert error.details == %{dependency: :postgres}
    assert Exception.message(error) == "build_broken:dependency_unavailable"
  end
end
