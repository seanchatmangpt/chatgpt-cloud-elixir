defmodule ChatGPTCloud.RuntimeIntegration.SparkContractTest do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.RuntimeIntegration.SparkContract

  test "requires the complete declared Spark extension set" do
    extensions = [:ash_json_api, :ash_graphql, :ash_ai, :ash_state_machine, :ash_archival]
    assert :ok = SparkContract.verify(extensions)

    assert {:error, {:missing_extensions, [:ash_ai]}} =
             SparkContract.verify(List.delete(extensions, :ash_ai))
  end
end
