defmodule ChatGPTCloud.RuntimeIntegration.ApiOperationAdmissionTest do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.RuntimeIntegration.{ApiOperationAdmission, ApiProjectionContract}

  test "projected reads admit while mutations require construction authority" do
    contract = %ApiProjectionContract{surface: :json_api, resource: :run, operations: [:read, :update]}
    assert :ok = ApiOperationAdmission.admit(contract, :read, :select)
    assert {:error, :mutation_authority_required} = ApiOperationAdmission.admit(contract, :update, :select)
    assert :ok = ApiOperationAdmission.admit(contract, :update, :construct)
    assert {:error, :operation_not_projected} = ApiOperationAdmission.admit(contract, :destroy, :do)
  end
end
