defmodule ChatGPTCloudControlPlane.RuntimeContracts.StateMachineTerminal do
  @moduledoc "Requires terminal lifecycle states to be reached by an observed admitted transition."
  @terminal [:completed, :failed, :refused, :archived]

  def validate(state, %{transition_observed: true, transition_admitted: true}) when state in @terminal, do: :ok
  def validate(state, _) when state in @terminal, do: {:error, :implicit_terminal_state_refused}
  def validate(_, _), do: :ok
end
