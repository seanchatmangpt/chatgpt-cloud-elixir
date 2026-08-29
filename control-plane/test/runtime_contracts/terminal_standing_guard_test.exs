defmodule ChatGPTCloudControlPlane.RuntimeContracts.TerminalStandingGuardTest do
  use ExUnit.Case, async: true
  alias ChatGPTCloudControlPlane.RuntimeContracts.TerminalStandingGuard

  test "ALIVE requires exact execution" do
    assert :ok = TerminalStandingGuard.admit(%{standing: :ALIVE, executed: true, exact_subject: true})
    assert {:error, :alive_requires_exact_execution} = TerminalStandingGuard.admit(%{standing: :ALIVE})
  end
end
