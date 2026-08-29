defmodule ChatGPTCloud.RuntimeIntegration.IgniterPlanTest do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.RuntimeIntegration.IgniterPlan

  test "manufacture plan is stable and includes the admitted runtime extensions" do
    extensions = IgniterPlan.extensions()
    assert :reactor in extensions
    assert :ash_json_api in extensions
    assert :ash_authentication in extensions
    assert :ash_oban in extensions
    assert :ash_ai in extensions
    assert byte_size(IgniterPlan.fingerprint()) == 64
    assert IgniterPlan.fingerprint() == IgniterPlan.fingerprint()
  end
end
