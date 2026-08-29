defmodule ChatGPTCloud.RuntimeIntegration.ReactorStepContractTest do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.RuntimeIntegration.ReactorStepContract

  test "consequential reactor step must be idempotent and compensatable" do
    assert ReactorStepContract.valid?(%ReactorStepContract{name: :persist, idempotent: true, compensation: :rollback, consequential: true})
    refute ReactorStepContract.valid?(%ReactorStepContract{name: :persist, idempotent: false, compensation: nil, consequential: true})
    assert ReactorStepContract.valid?(%ReactorStepContract{name: :inspect, idempotent: true, compensation: nil, consequential: false})
  end
end
