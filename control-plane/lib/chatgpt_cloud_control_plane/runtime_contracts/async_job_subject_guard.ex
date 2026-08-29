defmodule ChatGPTCloudControlPlane.RuntimeContracts.AsyncJobSubjectGuard do
  @moduledoc "Prevents durable jobs from silently moving away from their admitted exact subject."

  def admit(%{admitted_sha: sha, execution_sha: sha}) when is_binary(sha) and sha != "", do: :ok
  def admit(%{admitted_sha: admitted, execution_sha: actual}), do: {:error, {:async_subject_drift, admitted, actual}}
  def admit(_), do: {:error, :invalid_async_job_subject}
end
