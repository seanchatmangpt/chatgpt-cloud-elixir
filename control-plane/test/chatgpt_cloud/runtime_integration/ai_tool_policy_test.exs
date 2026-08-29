defmodule ChatGPTCloud.RuntimeIntegration.AiToolPolicyTest do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.RuntimeIntegration.AiToolPolicy

  test "AshAI may query but cannot acquire mutation authority" do
    assert :ok = AiToolPolicy.admit(:query)
    assert {:error, :ai_actuation_forbidden} = AiToolPolicy.admit(:update)
    assert {:error, :ai_actuation_forbidden} = AiToolPolicy.admit(:destroy)
  end
end
