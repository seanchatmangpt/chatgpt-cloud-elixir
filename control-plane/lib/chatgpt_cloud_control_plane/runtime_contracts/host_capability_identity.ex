defmodule ChatGPTCloudControlPlane.RuntimeContracts.HostCapabilityIdentity do
  @moduledoc "Binds consequential runtime execution to an explicit host capability identity."

  def validate(%{host: host, capability_digest: digest, capabilities: capabilities})
      when is_binary(host) and host != "" and is_binary(digest) and digest != "" and is_list(capabilities) and capabilities != [], do: :ok

  def validate(_), do: {:error, :invalid_host_capability_identity}
end
