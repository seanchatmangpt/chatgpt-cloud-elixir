defmodule ChatGPTCloudControlPlane.RuntimeContracts.InvocationReceiptTest do
  use ExUnit.Case, async: true
  alias ChatGPTCloudControlPlane.RuntimeContracts.InvocationReceipt

  test "requires subject adapter runtime policy and IO receipt identity" do
    assert :ok = InvocationReceipt.validate(%{subject_sha: "s", adapter_digest: "a", runtime_digest: "r", policy_digest: "p", input_digest: "i", output_digest: "o"})
    assert {:error, {:missing_invocation_receipt_field, :policy_digest}} = InvocationReceipt.validate(%{subject_sha: "s", adapter_digest: "a", runtime_digest: "r", input_digest: "i", output_digest: "o"})
  end
end
