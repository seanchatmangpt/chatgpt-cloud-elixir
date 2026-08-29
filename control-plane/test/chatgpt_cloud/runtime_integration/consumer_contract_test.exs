defmodule ChatGPTCloud.RuntimeIntegration.ConsumerContractTest do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.RuntimeIntegration.ConsumerContract

  test "requires a full exact primitive SHA" do
    exact = %ConsumerContract{primitive: "ash-runtime", primitive_sha: String.duplicate("a", 40), manufacture: "ggen sync run", verify: "mix test"}
    short = %{exact | primitive_sha: "abc"}
    assert ConsumerContract.exact?(exact)
    refute ConsumerContract.exact?(short)
  end
end
