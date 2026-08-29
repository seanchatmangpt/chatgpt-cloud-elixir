defmodule ChatGPTCloudControlPlane.RuntimeContracts.ObanRetryGuard do
  @moduledoc "Requires retries to carry a changed hypothesis or transient-class evidence."

  def admit(%{attempt: attempt, changed_hypothesis: true}) when is_integer(attempt) and attempt > 1, do: :ok
  def admit(%{attempt: attempt, transient: true}) when is_integer(attempt) and attempt > 1, do: :ok
  def admit(%{attempt: 1}), do: :ok
  def admit(%{attempt: attempt}) when is_integer(attempt), do: {:error, :unchanged_retry_refused}
  def admit(_), do: {:error, :invalid_retry_contract}
end
