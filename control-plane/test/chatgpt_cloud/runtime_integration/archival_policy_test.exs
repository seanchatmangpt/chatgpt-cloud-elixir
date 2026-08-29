defmodule ChatGPTCloud.RuntimeIntegration.ArchivalPolicyTest do
  use ExUnit.Case, async: true
  alias ChatGPTCloud.RuntimeIntegration.ArchivalPolicy

  test "process evidence is archived rather than hard-deleted" do
    for kind <- [:receipt, :event, :qualification, :refusal] do
      assert :archive = ArchivalPolicy.disposition(kind)
    end

    assert :retain = ArchivalPolicy.disposition(:ephemeral_projection)
  end
end
