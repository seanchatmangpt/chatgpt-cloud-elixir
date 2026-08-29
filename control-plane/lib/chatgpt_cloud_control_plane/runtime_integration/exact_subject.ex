defmodule ChatGPTCloud.RuntimeIntegration.ExactSubject do
  @moduledoc "Binds runtime work to one exact repository/ref/SHA subject."
  @enforce_keys [:repository, :ref, :sha]
  defstruct [:repository, :ref, :sha]

  @type t :: %__MODULE__{repository: String.t(), ref: String.t(), sha: String.t()}

  @spec new(String.t(), String.t(), String.t()) :: {:ok, t()} | {:error, :invalid_sha}
  def new(repo, ref, sha) when is_binary(repo) and is_binary(ref) and is_binary(sha) do
    if byte_size(sha) == 40,
      do: {:ok, %__MODULE__{repository: repo, ref: ref, sha: sha}},
      else: {:error, :invalid_sha}
  end
end
