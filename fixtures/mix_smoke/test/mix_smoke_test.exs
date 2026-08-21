defmodule MixSmokeTest do
  use ExUnit.Case, async: true

  test "plain Mix/ExUnit executes" do
    assert MixSmoke.add(20, 22) == 42
  end
end
