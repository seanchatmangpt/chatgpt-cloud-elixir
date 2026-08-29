defmodule ChatGPTCloud.RuntimeIntegration.RuntimeEcosystemReceipt do
  @moduledoc """Machine-readable qualification receipt binding source, runtime manifest and observed execution."""

  @enforce_keys [:subject_sha, :manifest_digest, :command, :exit_code]
  defstruct [:subject_sha, :manifest_digest, :command, :exit_code, standing: :unknown]

  @type t :: %__MODULE__{
          subject_sha: String.t(),
          manifest_digest: String.t(),
          command: String.t(),
          exit_code: integer(),
          standing: atom()
        }

  @spec alive?(t(), String.t()) :: boolean()
  def alive?(%__MODULE__{subject_sha: sha, exit_code: 0, standing: :alive}, exact_sha), do: sha == exact_sha
  def alive?(_, _), do: false

  @spec identity(t()) :: String.t()
  def identity(%__MODULE__{} = receipt) do
    :crypto.hash(
      :sha256,
      :erlang.term_to_binary({receipt.subject_sha, receipt.manifest_digest, receipt.command, receipt.exit_code, receipt.standing})
    )
    |> Base.encode16(case: :lower)
  end
end
