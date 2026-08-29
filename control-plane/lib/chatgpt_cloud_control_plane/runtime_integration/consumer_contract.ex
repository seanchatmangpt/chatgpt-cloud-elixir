defmodule ChatGPTCloud.RuntimeIntegration.ConsumerContract do
  @moduledoc "Binds a runtime consumer to exact GGen manufacture and verification commands."
  @enforce_keys [:primitive, :primitive_sha, :manufacture, :verify]
  defstruct [:primitive, :primitive_sha, :manufacture, :verify]

  @spec exact?(struct()) :: boolean()
  def exact?(%__MODULE__{primitive_sha: sha}), do: is_binary(sha) and byte_size(sha) == 40
end
