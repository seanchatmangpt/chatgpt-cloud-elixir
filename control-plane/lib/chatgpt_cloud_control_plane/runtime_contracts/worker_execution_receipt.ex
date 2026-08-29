defmodule ChatGPTCloudControlPlane.RuntimeContracts.WorkerExecutionReceipt do
  @moduledoc "Binds durable worker execution to exact job, subject, command, and exit evidence."

  def validate(%{job_id: job, subject_sha: sha, command: command, exit: exit})
      when is_binary(job) and job != "" and is_binary(sha) and sha != "" and is_binary(command) and command != "" and is_integer(exit), do: :ok

  def validate(_), do: {:error, :invalid_worker_execution_receipt}
end
