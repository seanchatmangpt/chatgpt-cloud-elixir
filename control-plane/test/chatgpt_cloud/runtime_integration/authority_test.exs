defmodule ChatGPTCloud.RuntimeIntegration.AuthorityTest do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.RuntimeIntegration.Authority

  test "construction authority does not imply consequential DO" do
    authority = %{select: true, construct: true, do: false}
    assert Authority.granted?(authority, :construct)
    refute Authority.granted?(authority, :do)
    assert {:error, :do_authority_required} = Authority.require_do(authority)
  end
end
