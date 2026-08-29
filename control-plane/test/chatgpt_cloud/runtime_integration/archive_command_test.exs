defmodule ChatGPTCloud.RuntimeIntegration.ArchiveCommandTest do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.RuntimeIntegration.ArchiveCommand

  test "archive preserves artifacts and refuses hard delete" do
    assert :ok = ArchiveCommand.admit(%ArchiveCommand{artifact_id: "artifact-1", reason: "retention transition"})
    assert {:error, :hard_delete_refused} = ArchiveCommand.admit(%ArchiveCommand{artifact_id: "artifact-1", reason: "cleanup", hard_delete: true})
  end
end
