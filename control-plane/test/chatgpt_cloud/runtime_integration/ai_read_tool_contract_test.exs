defmodule ChatGPTCloud.RuntimeIntegration.AiReadToolContractTest do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.RuntimeIntegration.AiReadToolContract

  test "AI tools are bounded to select-only read actions" do
    assert :ok = AiReadToolContract.admit(%AiReadToolContract{name: :read_run, resource: :run, action: :read})
    assert {:error, :invalid_ai_read_tool} = AiReadToolContract.admit(%AiReadToolContract{name: :deploy, resource: :release, action: :deploy})
    assert {:error, :ai_actuation_authority_refused} = AiReadToolContract.admit(%AiReadToolContract{name: :read_run, resource: :run, action: :read, authority: :do})
  end
end
