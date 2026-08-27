defmodule ChatGPTCloud.RuntimeIntegration.RetryPolicy do
  @moduledoc "Deterministic retry bounds for durable runtime work."
  @max_attempts %{qualification: 3, replay: 3, ingestion: 5, archival: 2}

  @spec retry?(atom(), non_neg_integer()) :: boolean()
  def retry?(queue, attempt), do: attempt < Map.get(@max_attempts, queue, 0)
end
