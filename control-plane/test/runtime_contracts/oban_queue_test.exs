defmodule ChatGPTCloudControlPlane.RuntimeContracts.ObanQueueTest do
  use ExUnit.Case, async: true
  alias ChatGPTCloudControlPlane.RuntimeContracts.ObanQueue
  test "requires queue and positive max attempts" do
    assert :ok = ObanQueue.validate(%{queue: :qualification, max_attempts: 5})
    assert {:error, :invalid_oban_queue_contract} = ObanQueue.validate(%{queue: :qualification, max_attempts: 0})
  end
end
