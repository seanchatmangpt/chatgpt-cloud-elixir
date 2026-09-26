defmodule ChatGPTCloudControlPlane.RuntimeContracts.GeneratedProjectionTest do
  use ExUnit.Case, async: true
  alias ChatGPTCloudControlPlane.RuntimeContracts.GeneratedProjection
  test "requires regeneration for generated outputs" do
    assert :ok = GeneratedProjection.validate(%{generated: true, mutation: :regenerate})
    assert {:error, :generated_projection_mutation_refused} = GeneratedProjection.validate(%{generated: true, mutation: :direct})
  end
end
