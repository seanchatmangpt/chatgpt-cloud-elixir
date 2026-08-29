defmodule ChatGPTCloud.RuntimeIntegration.AiReadToolContract do
  @moduledoc """Bounded AshAI tool declaration that cannot acquire mutation or deployment authority."""

  @enforce_keys [:name, :resource, :action]
  defstruct [:name, :resource, :action, authority: :select]

  @type t :: %__MODULE__{name: atom(), resource: atom(), action: atom(), authority: atom()}

  @spec admit(t()) :: :ok | {:error, atom()}
  def admit(%__MODULE__{name: name, resource: resource, action: action, authority: :select})
      when is_atom(name) and is_atom(resource) and action in [:read, :list, :query],
      do: :ok

  def admit(%__MODULE__{authority: _}), do: {:error, :ai_actuation_authority_refused}
  def admit(_), do: {:error, :invalid_ai_read_tool}
end
