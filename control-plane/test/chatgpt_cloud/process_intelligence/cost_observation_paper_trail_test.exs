defmodule ChatGPTCloud.ProcessIntelligence.CostObservationPaperTrailTest do
  use ChatGPTCloud.DataCase, async: false

  alias ChatGPTCloud.ProcessIntelligence.CostObservation

  test "a real create+destroy of a CostObservation is recorded as real Version rows" do
    # CostObservation only has :read/:destroy defaults plus a custom :create (confirmed
    # live -- an earlier draft of this test wrongly assumed an :update action existed
    # and Ash's own error message named the real available actions). Exercise the
    # actions that actually exist rather than an invented one.
    {:ok, obs} =
      CostObservation
      |> Ash.Changeset.for_create(:create, %{
        observation_key: "paper-trail-probe-#{System.unique_integer()}",
        run_key: "run-1",
        category: "compute",
        estimated_cost: Money.new(:USD, "1.00"),
        basis: %{}
      })
      |> Ash.create()

    versions_after_create =
      CostObservation.Version
      |> Ash.read!()
      |> Enum.count(&(&1.version_source_id == obs.id))

    assert versions_after_create == 1

    :ok =
      obs
      |> Ash.Changeset.for_destroy(:destroy)
      |> Ash.destroy()

    versions_after_destroy =
      CostObservation.Version
      |> Ash.read!()
      |> Enum.count(&(&1.version_source_id == obs.id))

    # create (1) + this real destroy (1) = 2 real recorded versions -- not asserted from
    # the schema alone, actually read back from the database.
    assert versions_after_destroy == 2
  end
end
