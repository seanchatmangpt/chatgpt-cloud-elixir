defmodule ChatGPTCloud.RuntimeIntegration.FalsifierTest do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.RuntimeIntegration.Falsifier

  test "evaluates exit and standing falsifiers against observed evidence" do
    exit_falsifier = %Falsifier{claim: "command succeeds", command: "mix test", failure_condition: {:exit_nonzero}}
    standing_falsifier = %Falsifier{claim: "subject alive", command: "verify", failure_condition: {:standing, :alive}}
    assert Falsifier.falsified?(exit_falsifier, %{exit_code: 1})
    refute Falsifier.falsified?(exit_falsifier, %{exit_code: 0})
    assert Falsifier.falsified?(standing_falsifier, %{standing: :build_broken})
  end
end
