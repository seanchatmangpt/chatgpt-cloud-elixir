defmodule ChatGPTCloudControlPlane.RuntimeContracts.IgniterManifestTest do
  use ExUnit.Case, async: true
  alias ChatGPTCloudControlPlane.RuntimeContracts.IgniterManifest
  test "requires generator version and digest" do
    assert :ok = IgniterManifest.validate(%{generator: "ecosystem", version: "1", digest: String.duplicate("d", 32)})
    assert {:error, :igniter_manifest_incomplete} = IgniterManifest.validate(%{generator: "ecosystem"})
  end
end
