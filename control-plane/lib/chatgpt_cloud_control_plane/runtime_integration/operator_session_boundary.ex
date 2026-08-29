defmodule ChatGPTCloud.RuntimeIntegration.OperatorSessionBoundary do
  @moduledoc """Admission boundary for browser/operator sessions without ambient machine authority."""

  @enforce_keys [:operator_id, :session_id]
  defstruct [:operator_id, :session_id, scopes: []]

  @type t :: %__MODULE__{operator_id: String.t(), session_id: String.t(), scopes: [atom()]}

  @spec admit(map()) :: {:ok, t()} | {:error, :operator_session_required}
  def admit(%{operator_id: operator_id, session_id: session_id} = attrs)
      when is_binary(operator_id) and operator_id != "" and is_binary(session_id) and session_id != "" do
    {:ok, %__MODULE__{operator_id: operator_id, session_id: session_id, scopes: Map.get(attrs, :scopes, [])}}
  end

  def admit(_), do: {:error, :operator_session_required}

  @spec permits?(t(), atom()) :: boolean()
  def permits?(%__MODULE__{scopes: scopes}, scope), do: scope in scopes
end
