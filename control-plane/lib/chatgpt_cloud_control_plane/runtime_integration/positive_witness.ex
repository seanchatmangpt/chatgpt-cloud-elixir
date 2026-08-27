defmodule ChatGPTCloud.RuntimeIntegration.PositiveWitness do
  @moduledoc "Observed positive witness bound to exact subject, command, and successful exit."
  @enforce_keys [:subject_sha, :command, :exit_code]
  defstruct [:subject_sha, :command, :exit_code, :evidence_digest]

  @spec valid?(struct()) :: boolean()
  def valid?(%__MODULE__{subject_sha: sha, exit_code: 0}), do: is_binary(sha) and byte_size(sha) == 40
  def valid?(%__MODULE__{}), do: false
end
