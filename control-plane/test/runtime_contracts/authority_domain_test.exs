defmodule ChatGPTCloudControlPlane.RuntimeContracts.AuthorityDomainTest do
  use ExUnit.Case, async: true
  alias ChatGPTCloudControlPlane.RuntimeContracts.AuthorityDomain
  test "admits only declared domains" do
    assert :ok = AuthorityDomain.validate(:github, [:github, :project2])
    assert {:error, {:authority_domain_refused, :deploy}} = AuthorityDomain.validate(:deploy, [:github, :project2])
  end
end
