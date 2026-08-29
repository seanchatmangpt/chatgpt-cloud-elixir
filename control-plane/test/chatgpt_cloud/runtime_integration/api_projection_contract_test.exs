defmodule ChatGPTCloud.RuntimeIntegration.ApiProjectionContractTest do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.RuntimeIntegration.ApiProjectionContract

  test "projection supports declared machine surfaces and explicit operations" do
    contract = %ApiProjectionContract{surface: :json_api, resource: :run, operations: [:read, :update]}
    assert ApiProjectionContract.valid?(contract)
    assert ApiProjectionContract.mutation?(:update)
    refute ApiProjectionContract.valid?(%{contract | surface: :ambient_rpc})
  end
end
