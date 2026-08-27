defmodule ChatGPTCloud.RuntimeIntegration.ReadProjectionTest do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.RuntimeIntegration.ReadProjection

  test "read projection names fields and carries no mutation authority" do
    projection = %ReadProjection{name: :run_summary, fields: [:id, :standing], authority: :select}
    assert ReadProjection.valid?(projection)
    refute ReadProjection.valid?(%{projection | authority: :construct})
  end
end
