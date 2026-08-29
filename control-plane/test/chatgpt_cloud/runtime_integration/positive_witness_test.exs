defmodule ChatGPTCloud.RuntimeIntegration.PositiveWitnessTest do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.RuntimeIntegration.PositiveWitness

  test "witness is positive only for successful exact-subject execution" do
    sha = String.duplicate("c", 40)
    witness = %PositiveWitness{subject_sha: sha, command: "mix test", exit_code: 0}
    assert PositiveWitness.positive?(witness, sha)
    refute PositiveWitness.positive?(%{witness | exit_code: 1}, sha)
    refute PositiveWitness.positive?(witness, String.duplicate("d", 40))
  end
end
