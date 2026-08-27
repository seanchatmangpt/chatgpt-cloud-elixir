defmodule ChatGPTCloud.RuntimeIntegration.AshActionContractTest do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.RuntimeIntegration.AshActionContract

  test "read actions remain non-actuating while mutations require construction authority" do
    assert AshActionContract.valid?(%AshActionContract{resource: :run, action: :read, type: :read, authority: :select})
    assert AshActionContract.valid?(%AshActionContract{resource: :run, action: :update, type: :update, authority: :construct})
    refute AshActionContract.valid?(%AshActionContract{resource: :run, action: :update, type: :update, authority: :select})
  end
end
