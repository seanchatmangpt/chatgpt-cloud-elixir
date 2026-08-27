defmodule ChatGPTCloud.RuntimeIntegration.ArchiveCommand do
  @moduledoc """Typed archival command for process artifacts that must not be hard-deleted."""

  @enforce_keys [:artifact_id, :reason]
  defstruct [:artifact_id, :reason, hard_delete: false]

  @type t :: %__MODULE__{artifact_id: String.t(), reason: String.t(), hard_delete: boolean()}

  @spec admit(t()) :: :ok | {:error, atom()}
  def admit(%__MODULE__{artifact_id: id, reason: reason, hard_delete: false})
      when is_binary(id) and id != "" and is_binary(reason) and reason != "",
      do: :ok

  def admit(%__MODULE__{hard_delete: true}), do: {:error, :hard_delete_refused}
  def admit(_), do: {:error, :invalid_archive_command}
end
