defmodule ChatGPTCloud.RuntimeIntegration.StateTransitionRequest do
  @moduledoc """Explicit run lifecycle transition request; terminal standing is never implicit."""

  @terminal [:alive, :partial_alive, :build_broken, :blocked, :refused]
  @enforce_keys [:run_id, :from, :to, :reason]
  defstruct [:run_id, :from, :to, :reason]

  @type t :: %__MODULE__{run_id: String.t(), from: atom(), to: atom(), reason: String.t()}

  @spec admit(t()) :: :ok | {:error, atom()}
  def admit(%__MODULE__{run_id: run_id, from: from, to: to, reason: reason})
      when is_binary(run_id) and run_id != "" and is_atom(from) and is_atom(to) and
             is_binary(reason) and reason != "" and from != to,
      do: :ok

  def admit(_), do: {:error, :invalid_state_transition}

  @spec terminal?(t()) :: boolean()
  def terminal?(%__MODULE__{to: to}), do: to in @terminal
end
