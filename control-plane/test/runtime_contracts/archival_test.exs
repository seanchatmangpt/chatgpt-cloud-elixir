defmodule ChatGPTCloudControlPlane.RuntimeContracts.ArchivalTest do
  use ExUnit.Case, async: true
  alias ChatGPTCloudControlPlane.RuntimeContracts.Archival
  test "archives instead of hard deleting" do
    assert :ok = Archival.validate(:archive)
    assert {:error, :hard_delete_refused} = Archival.validate(:delete)
  end
end
