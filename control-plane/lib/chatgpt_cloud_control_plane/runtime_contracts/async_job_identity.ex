defmodule ChatGPTCloudControlPlane.RuntimeContracts.AsyncJobIdentity do
  @moduledoc "Binds durable jobs to exact subject, queue, worker and idempotency identity."
  def validate(%{subject_digest: s, queue: q, worker: w, idempotency_key: k}) when is_binary(s) and byte_size(s) >= 32 and is_atom(q) and is_atom(w) and is_binary(k) and byte_size(k) >= 16, do: :ok
  def validate(_), do: {:error, :async_job_identity_incomplete}
end
