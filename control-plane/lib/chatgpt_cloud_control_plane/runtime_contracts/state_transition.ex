defmodule ChatGPTCloudControlPlane.RuntimeContracts.StateTransition do
  @moduledoc "Allows only declared lifecycle edges; terminal states cannot manufacture successors."
  @terminal [:completed, :failed, :refused, :archived]

  def validate(from, to, allowed) when is_list(allowed) do
    cond do
      from in @terminal -> {:error, :terminal_state_transition}
      {from, to} in allowed -> :ok
      true -> {:error, {:transition_not_admitted, from, to}}
    end
  end
end
