defmodule ChatGPTCloud.RuntimeIntegration.EventEnvelopeTest do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.RuntimeIntegration.EventEnvelope

  test "observational event envelopes do not acquire DO authority" do
    observed = %EventEnvelope{type: :qualification, subject: "s", payload: %{}, authority: :observe}
    actuating = %{observed | authority: :do}
    refute EventEnvelope.actuating?(observed)
    assert EventEnvelope.actuating?(actuating)
  end
end
