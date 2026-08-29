defmodule ChatGPTCloud.RuntimeIntegration.EnvironmentObservationTest do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.RuntimeIntegration.EnvironmentObservation

  test "reports only explicitly observed service availability" do
    observation = %EnvironmentObservation{platform: :linux, architecture: :x86_64, services: %{postgres: true, fly: false}}
    assert EnvironmentObservation.supports?(observation, :postgres)
    refute EnvironmentObservation.supports?(observation, :fly)
    refute EnvironmentObservation.supports?(observation, :redis)
  end
end
