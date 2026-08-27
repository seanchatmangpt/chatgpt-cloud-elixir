defmodule ChatGPTCloud.RuntimeIntegration.QualificationJobContract do
  @moduledoc """Durable qualification work contract suitable for an AshOban boundary."""

  @enforce_keys [:subject_sha, :command, :attempt]
  defstruct [:subject_sha, :command, :attempt, max_attempts: 3]

  @spec admit(t()) :: :ok | {:error, atom()} when t: %__MODULE__{}
  def admit(%__MODULE__{subject_sha: sha, command: command, attempt: attempt, max_attempts: max})
      when is_binary(sha) and byte_size(sha) == 40 and is_binary(command) and command != "" and
             is_integer(attempt) and attempt >= 1 and is_integer(max) and attempt <= max,
      do: :ok

  def admit(%__MODULE__{attempt: attempt, max_attempts: max}) when is_integer(attempt) and is_integer(max) and attempt > max,
    do: {:error, :retry_budget_exhausted}

  def admit(_), do: {:error, :invalid_qualification_job}
end
