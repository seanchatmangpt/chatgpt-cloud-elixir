defmodule ChatGPTCloud.RuntimeIntegration.RuntimeEcosystemReceiptTest do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.RuntimeIntegration.RuntimeEcosystemReceipt

  test "alive requires successful execution on the exact receipt subject" do
    sha = String.duplicate("3", 40)
    receipt = %RuntimeEcosystemReceipt{subject_sha: sha, manifest_digest: "manifest-1", command: "mix test", exit_code: 0, standing: :alive}
    assert RuntimeEcosystemReceipt.alive?(receipt, sha)
    refute RuntimeEcosystemReceipt.alive?(receipt, String.duplicate("4", 40))
    assert byte_size(RuntimeEcosystemReceipt.identity(receipt)) == 64
  end
end
