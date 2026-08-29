defmodule ChatGPTCloud.RuntimeIntegration.QueuePolicyTest do
  use ExUnit.Case, async: true
  alias ChatGPTCloud.RuntimeIntegration.QueuePolicy

  test "admits bounded known queues and refuses undeclared queues" do
    assert {:ok, 4} = QueuePolicy.concurrency(:qualification)
    assert {:ok, 8} = QueuePolicy.concurrency(:ingestion)
    assert {:error, :unknown_queue} = QueuePolicy.concurrency(:deploy)
  end
end
