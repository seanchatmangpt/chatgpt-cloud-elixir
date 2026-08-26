defmodule ChatGPTCloud.SwarmCoordination.Project2Test do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.SwarmCoordination.Project2

  test "Project memory records are control state, not work demand" do
    refute Project2.work_candidate?(%{
             item_id: "memory-item",
             type: "DRAFT_ISSUE",
             body: "<!-- chatgpt-project-memory:v1 ZGZjbS9mcm9udGllci9jdXJyZW50 -->\ncontrol state"
           })
  end

  test "ordinary Project items remain eligible demand" do
    assert Project2.work_candidate?(%{
             item_id: "issue-item",
             type: "ISSUE",
             body: "Implement the admitted feature",
             is_archived: false
           })

    refute Project2.work_candidate?(%{
             item_id: "archived-item",
             type: "ISSUE",
             body: "old work",
             is_archived: true
           })
  end
end
