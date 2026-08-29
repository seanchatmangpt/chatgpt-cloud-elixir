defmodule ChatGPTCloud.RuntimeIntegration.ExtensionManifestTest do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.RuntimeIntegration.ExtensionManifest

  test "maps admitted extensions to explicit production responsibilities" do
    assert {:ok, :orchestration} = ExtensionManifest.role(:reactor)
    assert {:ok, :reproducible_manufacture} = ExtensionManifest.role(:igniter)
    assert {:ok, :bounded_ai_queries} = ExtensionManifest.role(:ash_ai)
    assert {:error, :unknown_extension} = ExtensionManifest.role(:ambient_do)
  end
end
