defmodule ChatGPTCloud.RuntimeIntegration.Lifecycle do
  @moduledoc "Typed lifecycle transition table for runtime runs."
  @transitions %{
    pending: [:admitted, :refused],
    admitted: [:running, :refused],
    running: [:qualified, :failed, :blocked],
    qualified: [:archived],
    failed: [:running, :archived],
    blocked: [:running, :archived],
    refused: [:archived],
    archived: []
  }

  @spec allowed?(atom(), atom()) :: boolean()
  def allowed?(from, to), do: to in Map.get(@transitions, from, [])
end
