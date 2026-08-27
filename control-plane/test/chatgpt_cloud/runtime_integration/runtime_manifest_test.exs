defmodule ChatGPTCloud.RuntimeIntegration.RuntimeManifestTest do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.RuntimeIntegration.RuntimeManifest

  test "manifest requires the admitted runtime roles and PI ownership fence" do
    manifest = RuntimeManifest.current()
    assert :reactor in manifest.extensions
    assert :ash_oban in manifest.extensions
    assert :ash_state_machine in manifest.extensions
    assert manifest.process_intelligence_owner in ["wasm4pm", "wasm4pm-compat"]
    assert RuntimeManifest.closed?(manifest)
  end
end
