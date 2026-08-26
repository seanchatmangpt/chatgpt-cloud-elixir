defmodule ChatGPTCloud.SwarmCoordination.CoordinatorTest do
  use ChatGPTCloud.DataCase, async: false

  alias ChatGPTCloud.SwarmCoordination.{Coordinator, Project2}

  test "JSON work control preserves the BRCE authority fence and exclusive claim ownership" do
    assert {:ok, pending, enqueue_receipt} =
             Coordinator.enqueue(%{
               "work_item_id" => "work_test_exclusive_claim",
               "work_type" => "implementation",
               "description" => "Implement SwarmSH work control",
               "priority" => "high",
               "authority" => %{"do" => %{"granted" => true}}
             })

    assert pending["schema"] == "swarmsh.work/v1"
    assert pending["status"] == "pending"
    assert pending["authority"]["construct"]["granted"] == true
    assert pending["authority"]["do"] == %{"granted" => false, "requires" => "BRCE"}
    assert enqueue_receipt["event_type"] == "enqueued"

    assert {:error, %{"standing" => "REFUSED", "type" => "INVALID_AGENT_ID"}} =
             Coordinator.claim("work_test_exclusive_claim", "")

    assert {:ok, claimed, claim_receipt} =
             Coordinator.claim("work_test_exclusive_claim", "chatgpt-agent-1")

    assert claimed["status"] == "active"
    assert claimed["agent_id"] == "chatgpt-agent-1"
    assert claim_receipt["event_type"] == "claimed"

    assert {:error,
            %{
              "standing" => "REFUSED",
              "type" => "CLAIM_CONFLICT",
              "details" => %{
                "claimed_by" => "chatgpt-agent-1",
                "requested_by" => "chatgpt-agent-2"
              }
            }} = Coordinator.claim("work_test_exclusive_claim", "chatgpt-agent-2")
  end

  test "progress and completion are owner-gated and completion is not an automatic ALIVE crown" do
    assert {:ok, _, _} =
             Coordinator.enqueue(%{
               work_item_id: "work_test_lifecycle",
               work_type: "qualification",
               description: "Run exact-head qualification"
             })

    assert {:ok, _, _} = Coordinator.claim("work_test_lifecycle", "agent-a")

    assert {:error, %{"type" => "NOT_CLAIM_OWNER"}} =
             Coordinator.progress("work_test_lifecycle", "agent-b", 50)

    assert {:ok, in_progress, progress_receipt} =
             Coordinator.progress("work_test_lifecycle", "agent-a", 50)

    assert in_progress["status"] == "in_progress"
    assert in_progress["progress"] == 50
    assert progress_receipt["event_type"] == "progress"

    assert {:ok, completed, completion_receipt} =
             Coordinator.complete("work_test_lifecycle", "agent-a", %{
               "command" => "mix test",
               "exit" => 0
             })

    assert completed["status"] == "completed"
    assert completed["progress"] == 100
    assert completion_receipt["standing"] == "PARTIAL_ALIVE"
    assert String.length(completion_receipt["digest"]) == 64

    assert {:error, %{"type" => "INVALID_TRANSITION"}} =
             Coordinator.complete("work_test_lifecycle", "agent-a")
  end

  test "explicit observed standing may crown a completion receipt" do
    assert {:ok, _, _} =
             Coordinator.enqueue(%{
               work_item_id: "work_test_alive",
               work_type: "verification",
               description: "Observe exact admitted acceptance command"
             })

    assert {:ok, _, _} = Coordinator.claim("work_test_alive", "verifier")

    assert {:ok, _, receipt} =
             Coordinator.complete("work_test_alive", "verifier", %{
               "standing" => "ALIVE",
               "subject_sha" => "abc123",
               "command" => "mix test",
               "exit" => 0
             })

    assert receipt["standing"] == "ALIVE"
  end

  test "Project 2 items map to deterministic replayable work identities" do
    item = %{
      item_id: "PVTI_example",
      type: "ISSUE",
      title: "Finish SwarmSH integration",
      body: "Use JSON control objects",
      repository: "seanchatmangpt/chatgpt-cloud-elixir",
      number: 42,
      state: "OPEN",
      field_values: %{"Priority" => "High"}
    }

    first = Project2.project_item_to_work(item)
    second = Project2.project_item_to_work(item)

    assert first.work_item_id == second.work_item_id
    assert String.starts_with?(first.work_item_id, "project2_")
    assert first.priority == "high"
    assert first.subject["repository"] == "seanchatmangpt/chatgpt-cloud-elixir"
  end
end
