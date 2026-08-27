defmodule ChatGPTCloud.RuntimeIntegration.SparkContractTest do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.RuntimeIntegration.SparkContract

  test "compile-time contract requires standing authority and extension wiring" do
    assert :ok = SparkContract.validate(%{standing: true, authority: true, extensions: true})
    assert {:error, :missing_standing_contract} = SparkContract.validate(%{standing: false, authority: true, extensions: true})
    assert {:error, :missing_authority_contract} = SparkContract.validate(%{standing: true, authority: false, extensions: true})
  end
end
