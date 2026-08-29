defmodule ChatGPTCloud.RuntimeIntegration.WorkerReceiptTest do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.RuntimeIntegration.WorkerReceipt

  test "only explicit ok results are successful" do
    ok = %WorkerReceipt{queue: :qualification, attempt: 1, idempotency_key: "run-1", result: :ok}
    failed = %{ok | result: {:error, :timeout}}
    assert WorkerReceipt.successful?(ok)
    refute WorkerReceipt.successful?(failed)
  end
end
