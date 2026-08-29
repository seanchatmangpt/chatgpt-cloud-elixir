defmodule ChatGPTCloud.RuntimeIntegration.ReactorCompensationTest do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.RuntimeIntegration.ReactorCompensation

  test "consequential step requires named compensation" do
    assert :ok = ReactorCompensation.validate(%{consequential: true, compensation: :restore_previous})
    assert {:error, :compensation_required} = ReactorCompensation.validate(%{consequential: true, compensation: nil})
    assert :ok = ReactorCompensation.validate(%{consequential: false, compensation: nil})
  end
end
