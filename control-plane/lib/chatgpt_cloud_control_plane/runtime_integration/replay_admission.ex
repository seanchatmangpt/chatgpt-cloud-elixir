defmodule ChatGPTCloud.RuntimeIntegration.ReplayAdmission do
  @moduledoc """Admission rule that binds replay to the same exact subject as its source receipt."""

  @spec admit(String.t(), map()) :: :ok | {:error, atom()}
  def admit(subject_sha, %{subject_sha: receipt_sha, exit_code: 0})
      when is_binary(subject_sha) and byte_size(subject_sha) == 40 and subject_sha == receipt_sha,
      do: :ok

  def admit(_, %{exit_code: exit_code}) when exit_code != 0, do: {:error, :source_execution_failed}
  def admit(_, _), do: {:error, :receipt_subject_mismatch}
end
