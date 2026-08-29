defmodule ChatGPTCloudControlPlane.RuntimeContracts.AsyncJobIdentityTest do
  use ExUnit.Case, async: true
  alias ChatGPTCloudControlPlane.RuntimeContracts.AsyncJobIdentity

  test "requires subject queue worker and idempotency identity" do
    digest = String.duplicate("a", 32)
    assert :ok = AsyncJobIdentity.validate(%{subject_digest: digest, queue: :qualification, worker: :qualifier, idempotency_key: "0123456789abcdef"})
    assert {:error, :async_job_identity_incomplete} = AsyncJobIdentity.validate(%{subject_digest: digest, queue: :qualification})
  end
end
