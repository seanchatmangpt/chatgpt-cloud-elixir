defmodule AshPostgresIntegrationTest do
  use ExUnit.Case, async: false

  alias AshPostgresIntegration.Ticket

  setup do
    Ticket
    |> Ash.read!()
    |> Enum.each(&Ash.destroy!/1)

    :ok
  end

  test "real Ash create/read/update/destroy path executes through a live PostgreSQL 17 server" do
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

  test "validation failure is typed and does not actuate against the database" do
    assert_raise Ash.Error.Invalid, fn ->
      Ticket
      |> Ash.Changeset.for_create(:create, %{name: "negative", score: -1})
      |> Ash.create!()
    end

    assert Ash.read!(Ticket) == []
  end

  test "the unique_name identity is enforced by a real Postgres unique index" do
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
