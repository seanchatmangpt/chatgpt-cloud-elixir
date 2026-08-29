defmodule ChatGPTCloudControlPlane.RuntimeContracts.ActorTenantContextTest do
  use ExUnit.Case, async: true
  alias ChatGPTCloudControlPlane.RuntimeContracts.ActorTenantContext

  test "requires explicit actor and tenant context" do
    assert :ok = ActorTenantContext.validate(%{actor_id: "actor-1", tenant_id: "tenant-1"})
    assert {:error, :missing_actor_tenant_context} = ActorTenantContext.validate(%{actor_id: "actor-1"})
  end
end
