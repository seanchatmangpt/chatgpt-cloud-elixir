defmodule ChatGPTCloud.RuntimeIntegration.ActionEnvelopeTest do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.RuntimeIntegration.ActionEnvelope

  test "requires operation subject authority and replay identity" do
    envelope = ActionEnvelope.new(operation: :qualify, subject: "subject-1", authority: :construct, replay_key: "rk-1")
    assert envelope.operation == :qualify
    assert envelope.subject == "subject-1"
    assert envelope.authority == :construct
    assert envelope.replay_key == "rk-1"
  end
end
