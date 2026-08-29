defmodule ChatGPTCloud.RuntimeIntegration.ReplayJobContract do
  @moduledoc """Replay job contract that requires an exact subject and source receipt."""

  @enforce_keys [:subject_sha, :receipt_id, :replay_key]
  defstruct [:subject_sha, :receipt_id, :replay_key]

  @type t :: %__MODULE__{subject_sha: String.t(), receipt_id: String.t(), replay_key: String.t()}

  @spec admit(t()) :: :ok | {:error, :invalid_replay_job}
  def admit(%__MODULE__{subject_sha: sha, receipt_id: receipt_id, replay_key: replay_key})
      when is_binary(sha) and byte_size(sha) == 40 and is_binary(receipt_id) and receipt_id != "" and
             is_binary(replay_key) and replay_key != "",
      do: :ok

  def admit(_), do: {:error, :invalid_replay_job}
end
