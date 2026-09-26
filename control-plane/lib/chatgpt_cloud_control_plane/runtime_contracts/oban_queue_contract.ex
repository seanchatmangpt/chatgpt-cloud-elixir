defmodule ChatGPTCloudControlPlane.RuntimeContracts.ObanQueueContract do
  @moduledoc "Maps durable runtime work to explicit Oban queues and bounded retry policies."

  @queues %{qualification: 3, replay: 3, mining: 2, ingestion: 5}

  def policy(kind) when is_map_key(@queues, kind), do: {:ok, %{queue: kind, max_attempts: Map.fetch!(@queues, kind)}}
  def policy(kind), do: {:error, {:unsupported_job_kind, kind}}
end
