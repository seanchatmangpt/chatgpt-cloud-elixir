defmodule ChatGPTCloudControlPlane.RuntimeContracts.CorrelationCausationTest do
  use ExUnit.Case, async: true
  alias ChatGPTCloudControlPlane.RuntimeContracts.CorrelationCausation

  test "requires distributed invocation lineage" do
    assert :ok = CorrelationCausation.validate(%{correlation_id: "corr", causation_id: "cause"})
    assert {:error, :missing_correlation_causation} = CorrelationCausation.validate(%{correlation_id: "corr"})
  end
end
