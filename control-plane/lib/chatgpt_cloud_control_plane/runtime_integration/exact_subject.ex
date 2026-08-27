defmodule ChatGPTCloud.RuntimeIntegration.ExactSubject do
  @moduledoc "Binds runtime work to one exact repository/ref/SHA subject."
  @enforce_keys [:repository, :ref, :sha]
  defstruct [:repository, :ref, :sha]

  @spec new(String.t(), String.t(), String.t()) :: {:ok, struct()} | {:error, atom()}
  def new(repo, ref, sha) when is_binary(repo) and is_binary(ref) and is_binary(sha) do
    if byte_size(sha) == 40, do: {:ok, %__MODULE__{repository: repo, ref: ref, sha: sha}}, else: {:error, :invalid_sha}
  end
end
