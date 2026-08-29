defmodule ChatGPTCloudControlPlane.RuntimeContracts.TerminalStandingGuard do
  @moduledoc "Prevents terminal standing from being inferred without exact execution evidence."

  def admit(%{standing: standing, executed: true, exact_subject: true}) when standing in [:ALIVE, :PARTIAL_ALIVE], do: :ok
  def admit(%{standing: :ALIVE}), do: {:error, :alive_requires_exact_execution}
  def admit(%{standing: standing}) when standing in [:UNKNOWN, :PARTIAL_ALIVE, :BLOCKED, :BUILD_BROKEN, :UNSUPPORTED], do: :ok
  def admit(_), do: {:error, :invalid_standing_evidence}
end
