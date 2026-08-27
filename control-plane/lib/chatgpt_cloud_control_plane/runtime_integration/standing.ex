defmodule ChatGPTCloud.RuntimeIntegration.Standing do
  @moduledoc "Typed runtime standing used at integration boundaries."

  @values [:unknown, :partial_alive, :alive, :blocked, :build_broken, :unsupported, :refused]

  @spec values() :: [atom()]
  def values, do: @values

  @spec terminal?(atom()) :: boolean()
  def terminal?(standing), do: standing in [:alive, :blocked, :build_broken, :unsupported, :refused]

  @spec valid?(atom()) :: boolean()
  def valid?(standing), do: standing in @values
end
