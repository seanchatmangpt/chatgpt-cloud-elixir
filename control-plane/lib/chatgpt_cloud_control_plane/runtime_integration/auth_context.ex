defmodule ChatGPTCloud.RuntimeIntegration.AuthContext do
  @moduledoc "Disjoint runtime identities for operators and agents."
  @enforce_keys [:kind, :principal]
  defstruct [:kind, :principal, scopes: []]

  @spec new(:operator | :agent, String.t(), [atom()]) :: struct()
  def new(kind, principal, scopes \\ [])
      when kind in [:operator, :agent] and is_binary(principal),
      do: %__MODULE__{kind: kind, principal: principal, scopes: scopes}
end
