defmodule AshEtsSmokeTest do
  use ExUnit.Case, async: false

  alias AshEtsSmoke.Ticket

  test "real Ash create/read/update/destroy path executes through ETS" do
    created =
      Ticket
      |> Ash.Changeset.for_create(:create, %{name: "ALIVE", score: 1})
      |> Ash.create!()

    assert created.id
    assert created.name == "ALIVE"
    assert created.score == 1

    [loaded] = Ash.read!(Ticket)
    assert loaded.id == created.id

    updated =
      created
      |> Ash.Changeset.for_update(:update, %{score: 2})
      |> Ash.update!()

    assert updated.score == 2

    Ash.destroy!(updated)
    assert Ash.read!(Ticket) == []
  end

  test "validation failure is typed and does not actuate" do
    assert_raise Ash.Error.Invalid, fn ->
      Ticket
      |> Ash.Changeset.for_create(:create, %{name: "negative", score: -1})
      |> Ash.create!()
    end

    assert Ash.read!(Ticket) == []
  end

  test "identity rejects duplicate names" do
    Ticket
    |> Ash.Changeset.for_create(:create, %{name: "unique", score: 0})
    |> Ash.create!()

    assert_raise Ash.Error.Invalid, fn ->
      Ticket
      |> Ash.Changeset.for_create(:create, %{name: "unique", score: 1})
      |> Ash.create!()
    end
  end
end
