defmodule ChatGPTCloud.RuntimeIntegration.QualificationStanding do
  @moduledoc """Standing derivation that refuses ALIVE from inspection or mismatched subjects."""

  @spec derive(String.t(), map()) :: atom()
  def derive(subject_sha, %{subject_sha: subject_sha, exit_code: 0, executed: true}), do: :alive
  def derive(_subject_sha, %{executed: false}), do: :unknown
  def derive(_subject_sha, %{exit_code: exit_code}) when is_integer(exit_code) and exit_code != 0, do: :build_broken
  def derive(_subject_sha, _), do: :unknown
end
