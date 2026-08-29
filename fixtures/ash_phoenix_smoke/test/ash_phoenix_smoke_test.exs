defmodule AshPhoenixSmokeTest do
  use ExUnit.Case, async: false

  alias AshPhoenixSmoke.Contact

  setup do
    Contact
    |> Ash.read!()
    |> Enum.each(&Ash.destroy!/1)

    :ok
  end

  test "AshPhoenix.Form drives a real create action end-to-end" do
    form =
      Contact
      |> AshPhoenix.Form.for_create(:create, domain: AshPhoenixSmoke.Domain)
      |> AshPhoenix.Form.validate(%{"name" => "Ada", "email" => "ada@example.com"})

    assert form.valid?

    assert {:ok, contact} = AshPhoenix.Form.submit(form)
    assert contact.name == "Ada"
    assert contact.email == "ada@example.com"

    [loaded] = Ash.read!(Contact)
    assert loaded.id == contact.id
  end

  test "AshPhoenix.Form surfaces real validation errors and does not actuate" do
    form =
      Contact
      |> AshPhoenix.Form.for_create(:create, domain: AshPhoenixSmoke.Domain)
      |> AshPhoenix.Form.validate(%{"name" => "Bad", "email" => "not-an-email"})

    refute form.valid?
    assert AshPhoenix.Form.errors(form) != []
    assert {:error, _form} = AshPhoenix.Form.submit(form)
    assert Ash.read!(Contact) == []
  end

  test "AshPhoenix.Form rejects a duplicate email identity" do
    assert {:ok, _first} =
             Contact
             |> AshPhoenix.Form.for_create(:create, domain: AshPhoenixSmoke.Domain)
             |> AshPhoenix.Form.validate(%{"name" => "First", "email" => "dup@example.com"})
             |> AshPhoenix.Form.submit()

    form =
      Contact
      |> AshPhoenix.Form.for_create(:create, domain: AshPhoenixSmoke.Domain)
      |> AshPhoenix.Form.validate(%{"name" => "Second", "email" => "dup@example.com"})

    assert {:error, _form} = AshPhoenix.Form.submit(form)
    assert length(Ash.read!(Contact)) == 1
  end
end
