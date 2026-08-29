defmodule ChatGPTCloud.RuntimeIntegration.JobKind do
  @moduledoc "Maps durable runtime jobs onto bounded AshOban queue identities."
  @queues %{
    qualification: :qualification,
    replay: :replay,
    ingestion: :ingestion,
    archival: :archival
  }

  @spec queue(atom()) :: {:ok, atom()} | {:error, :unsupported_job_kind}
  def queue(kind) do
    case Map.fetch(@queues, kind) do
      {:ok, queue} -> {:ok, queue}
      :error -> {:error, :unsupported_job_kind}
    end
  end
end
