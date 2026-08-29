defmodule ChatGPTCloudControlPlane.RuntimeContracts.StateTransitionGuard do
  @moduledoc "Enforces explicit lifecycle transitions; terminal states cannot be manufactured implicitly."

  @allowed %{
    pending: [:running, :refused],
    running: [:verifying, :failed, :refused],
    verifying: [:succeeded, :failed, :refused],
    failed: [:running, :refused],
    succeeded: [],
    refused: []
  }

  def admit(from, to) when is_atom(from) and is_atom(to) do
    if to in Map.get(@allowed, from, []), do: :ok, else: {:error, {:invalid_transition, from, to}}
  end
end
