defmodule ChatGPTCloudControlPlane.RuntimeContracts.GovernedAdapterIdentity do
  @moduledoc "Maps the local Ash/Reactor bridge onto the governed runtime adapter identity contract."

  def validate(%{adapter: adapter, version: version, digest: digest})
      when is_binary(adapter) and adapter != "" and is_binary(version) and version != "" and is_binary(digest) and digest != "", do: :ok

  def validate(_), do: {:error, :invalid_governed_adapter_identity}
end
