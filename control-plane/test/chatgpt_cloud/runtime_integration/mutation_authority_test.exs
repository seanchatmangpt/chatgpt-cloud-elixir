defmodule ChatGPTCloud.RuntimeIntegration.MutationAuthorityTest do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.RuntimeIntegration.MutationAuthority

  test "construct may mutate while select and observe cannot" do
    assert :ok = MutationAuthority.admit(:construct)
    assert {:error, :mutation_authority_required} = MutationAuthority.admit(:select)
    assert {:error, :mutation_authority_required} = MutationAuthority.admit(:observe)
  end
end
