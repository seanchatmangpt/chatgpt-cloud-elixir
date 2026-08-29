defmodule ChatGPTCloudControlPlane.RuntimeContracts.ExternalProcessIdentity do
  @moduledoc "Binds external-process adapters to executable and registry identity."

  def validate(%{executable: executable, executable_digest: digest, registry_id: registry})
      when is_binary(executable) and executable != "" and is_binary(digest) and digest != "" and is_binary(registry) and registry != "", do: :ok

  def validate(_), do: {:error, :invalid_external_process_identity}
end
