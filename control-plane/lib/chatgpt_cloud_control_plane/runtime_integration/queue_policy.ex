defmodule ChatGPTCloud.RuntimeIntegration.QueuePolicy do
  @moduledoc "Bounded queue names and concurrency hints for durable runtime work."
  @queues %{qualification: 4, replay: 4, ingestion: 8, archival: 2}

  @spec concurrency(atom()) :: {:ok, pos_integer()} | {:error, :unknown_queue}
  def concurrency(queue) do
    case Map.fetch(@queues, queue) do
      {:ok, value} -> {:ok, value}
      :error -> {:error, :unknown_queue}
    end
  end
end
