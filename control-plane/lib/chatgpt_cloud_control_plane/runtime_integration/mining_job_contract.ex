defmodule ChatGPTCloud.RuntimeIntegration.MiningJobContract do
  @moduledoc """Asynchronous mining request contract that references wasm4pm rather than embedding PI logic."""

  @enforce_keys [:subject_sha, :algorithm_ref]
  defstruct [:subject_sha, :algorithm_ref, owner: "wasm4pm"]

  @type t :: %__MODULE__{subject_sha: String.t(), algorithm_ref: String.t(), owner: String.t()}

  @spec admit(t()) :: :ok | {:error, atom()}
  def admit(%__MODULE__{subject_sha: sha, algorithm_ref: ref, owner: owner})
      when is_binary(sha) and byte_size(sha) == 40 and is_binary(ref) and ref != "" and owner in ["wasm4pm", "wasm4pm-compat"],
      do: :ok

  def admit(%__MODULE__{owner: _}), do: {:error, :process_intelligence_ownership_escape}
  def admit(_), do: {:error, :invalid_mining_job}
end
