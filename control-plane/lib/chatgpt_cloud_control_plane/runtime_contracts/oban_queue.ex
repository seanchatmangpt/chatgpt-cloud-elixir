defmodule ChatGPTCloudControlPlane.RuntimeContracts.ObanQueue do
  @moduledoc "Requires explicit durable queue and retry identity for asynchronous work."
  def validate(%{queue: q, max_attempts: n}) when is_atom(q) and is_integer(n) and n > 0, do: :ok
  def validate(_), do: {:error, :invalid_oban_queue_contract}
end
