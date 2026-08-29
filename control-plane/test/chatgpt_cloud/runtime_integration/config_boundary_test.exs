defmodule ChatGPTCloud.RuntimeIntegration.ConfigBoundaryTest do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.RuntimeIntegration.ConfigBoundary

  test "requires an explicit database URL and rejects empty configuration" do
    assert :ok = ConfigBoundary.validate(%{database_url: "ecto://db"})
    assert {:error, {:missing_config, [:database_url]}} = ConfigBoundary.validate(%{database_url: ""})
    assert {:error, {:missing_config, [:database_url]}} = ConfigBoundary.validate(%{})
  end
end
