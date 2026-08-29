defmodule ChatGPTCloud.RuntimeIntegration.AdmissionTest do
  use ExUnit.Case, async: true

  test "admits only exact subjects with complete capabilities and extension wiring" do
    input = %{
      repository: "seanchatmangpt/chatgpt-cloud-elixir",
      ref: "main",
      sha: String.duplicate("a", 40),
      required_capabilities: [:runtime, :reactor],
      available_capabilities: [:runtime, :reactor, :spark],
      extensions: [:ash_json_api, :ash_graphql, :ash_ai, :ash_state_machine, :ash_archival]
    }

    assert {:ok, %{sha: sha}} = ChatGPTCloud.RuntimeIntegration.admit(input)
    assert sha == String.duplicate("a", 40)
  end

  test "refuses missing runtime capability" do
    input = %{
      repository: "seanchatmangpt/chatgpt-cloud-elixir",
      ref: "main",
      sha: String.duplicate("b", 40),
      required_capabilities: [:runtime, :reactor],
      available_capabilities: [:runtime],
      extensions: [:ash_json_api, :ash_graphql, :ash_ai, :ash_state_machine, :ash_archival]
    }

    assert {:error, {:missing_capabilities, [:reactor]}} =
             ChatGPTCloud.RuntimeIntegration.admit(input)
  end
end
