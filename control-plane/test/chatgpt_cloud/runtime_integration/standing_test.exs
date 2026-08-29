defmodule ChatGPTCloud.RuntimeIntegration.StandingTest do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.RuntimeIntegration.Standing

  test "unknown and partial are intermediate while typed outcomes are terminal" do
    assert Standing.valid?(:unknown)
    assert Standing.valid?(:partial_alive)
    refute Standing.terminal?(:unknown)
    refute Standing.terminal?(:partial_alive)
    assert Standing.terminal?(:alive)
    assert Standing.terminal?(:blocked)
    assert Standing.terminal?(:refused)
    refute Standing.valid?(:fabricated)
  end
end
