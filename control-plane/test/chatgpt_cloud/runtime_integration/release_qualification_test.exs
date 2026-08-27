defmodule ChatGPTCloud.RuntimeIntegration.ReleaseQualificationTest do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.RuntimeIntegration.ReleaseQualification

  test "a built release may qualify without granting deployment authority" do
    qualification = %ReleaseQualification{release_built: true, image_built: true, deployment_authority: false}
    assert ReleaseQualification.qualified?(qualification)
    refute ReleaseQualification.deployable?(qualification)
    assert ReleaseQualification.deployable?(%{qualification | deployment_authority: true})
  end
end
