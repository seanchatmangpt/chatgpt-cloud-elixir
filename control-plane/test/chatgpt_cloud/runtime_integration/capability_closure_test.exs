defmodule ChatGPTCloud.RuntimeIntegration.CapabilityClosureTest do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.RuntimeIntegration.CapabilityClosure

  test "resolves transitive capabilities deterministically without duplicate nodes" do
    graph = %{ash_full: [:reactor, :api], reactor: [:spark], api: [:spark], spark: []}
    assert [:api, :ash_full, :reactor, :spark] = CapabilityClosure.resolve([:ash_full], graph)
  end
end
