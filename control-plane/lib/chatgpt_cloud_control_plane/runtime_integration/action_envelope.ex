defmodule ChatGPTCloud.RuntimeIntegration.ActionEnvelope do
  @moduledoc "Runtime action envelope that carries subject, authority, and replay identity."
  @enforce_keys [:operation, :subject, :authority, :replay_key]
  defstruct [:operation, :subject, :authority, :replay_key, input: %{}, metadata: %{}]

  @spec new(keyword()) :: struct()
  def new(opts), do: struct!(__MODULE__, opts)
end
