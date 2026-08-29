defmodule ChatGPTCloudControlPlane.RuntimeContracts.QualificationCommand do
  @moduledoc "Binds exact-head qualification to an explicit command and expected execution mode."

  def validate(%{sha: sha, command: command, mode: mode})
      when is_binary(sha) and sha != "" and is_binary(command) and command != "" and mode in [:local, :capsule, :ci_fallback], do: :ok

  def validate(_), do: {:error, :invalid_qualification_command}
end
