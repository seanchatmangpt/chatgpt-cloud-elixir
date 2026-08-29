defmodule ChatGPTCloud.RuntimeIntegration.QualificationReceipt do
  @moduledoc "Qualification receipt whose standing derives from observed command execution."
  @enforce_keys [:subject_sha, :command, :exit_code]
  defstruct [:subject_sha, :command, :exit_code, :output_digest]

  @spec standing(struct()) :: :alive | :build_broken
  def standing(%__MODULE__{exit_code: 0}), do: :alive
  def standing(%__MODULE__{}), do: :build_broken
end
