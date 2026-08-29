defmodule ChatGPTCloud.RuntimeIntegration.ActionAuthorityMatrixTest do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.RuntimeIntegration.ActionAuthorityMatrix

  test "read admits select while deploy requires DO" do
    assert :ok = ActionAuthorityMatrix.admit(:read, :select)
    assert {:error, :authority_refused} = ActionAuthorityMatrix.admit(:deploy, :construct)
    assert :ok = ActionAuthorityMatrix.admit(:deploy, :do)
    assert ActionAuthorityMatrix.permitted(:ingest) == [:construct, :do]
  end
end
