defmodule ChatGPTCloudControlPlane.RuntimeContracts.Project2OcelLineageTest do
  use ExUnit.Case, async: true
  alias ChatGPTCloudControlPlane.RuntimeContracts.Project2OcelLineage

  test "requires canonical Project 2 OCEL lineage" do
    assert :ok = Project2OcelLineage.validate(%{project: 2, ocel_key: "ggen/ecosystem/ocel/current", ocel_digest: "abc"})
    assert {:error, :invalid_project2_ocel_lineage} = Project2OcelLineage.validate(%{project: 2, ocel_key: "other", ocel_digest: "abc"})
  end
end
