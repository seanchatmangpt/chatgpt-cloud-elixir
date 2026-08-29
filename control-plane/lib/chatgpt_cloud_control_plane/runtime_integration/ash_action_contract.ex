defmodule ChatGPTCloud.RuntimeIntegration.AshActionContract do
  @moduledoc "Explicit contract for Ash actions crossing runtime boundaries."
  @enforce_keys [:resource, :action, :type]
  defstruct [:resource, :action, :type, inputs: [], outputs: [], authority: :construct]

  @spec valid?(struct()) :: boolean()
  def valid?(%__MODULE__{type: type, authority: authority})
      when type in [:read, :create, :update, :destroy, :action] do
    type == :read or authority in [:construct, :do]
  end

  def valid?(_), do: false
end
