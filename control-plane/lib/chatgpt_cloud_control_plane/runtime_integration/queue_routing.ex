defmodule ChatGPTCloud.RuntimeIntegration.QueueRouting do
  @moduledoc """Deterministic AshOban queue and retry routing for durable runtime work."""

  @routes %{
    qualification: %{queue: :qualification, max_attempts: 3},
    replay: %{queue: :replay, max_attempts: 3},
    mining: %{queue: :mining, max_attempts: 2}
  }

  @spec route(atom()) :: {:ok, map()} | {:error, :unknown_job_kind}
  def route(kind) do
    case Map.fetch(@routes, kind) do
      {:ok, route} -> {:ok, route}
      :error -> {:error, :unknown_job_kind}
    end
  end
end
