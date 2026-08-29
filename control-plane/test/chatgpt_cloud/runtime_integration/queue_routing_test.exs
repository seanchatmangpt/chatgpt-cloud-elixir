defmodule ChatGPTCloud.RuntimeIntegration.QueueRoutingTest do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.RuntimeIntegration.QueueRouting

  test "qualification replay and mining have deterministic queue routes" do
    assert {:ok, %{queue: :qualification, max_attempts: 3}} = QueueRouting.route(:qualification)
    assert {:ok, %{queue: :replay, max_attempts: 3}} = QueueRouting.route(:replay)
    assert {:ok, %{queue: :mining, max_attempts: 2}} = QueueRouting.route(:mining)
    assert {:error, :unknown_job_kind} = QueueRouting.route(:deploy)
  end
end
