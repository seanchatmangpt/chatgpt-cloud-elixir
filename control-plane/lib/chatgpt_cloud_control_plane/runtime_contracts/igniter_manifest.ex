defmodule ChatGPTCloudControlPlane.RuntimeContracts.IgniterManifest do
  @moduledoc "Requires reproducible ecosystem manufacture identity."
  def validate(%{generator: g, version: v, digest: d}) when is_binary(g) and is_binary(v) and is_binary(d) and byte_size(d) >= 32, do: :ok
  def validate(_), do: {:error, :igniter_manifest_incomplete}
end
