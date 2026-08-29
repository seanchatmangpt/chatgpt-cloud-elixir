defmodule ChatGPTCloudControlPlane.RuntimeContracts.ActorTenantContext do
  @moduledoc "Maps Ash actor/tenant context to the governed runtime adapter context contract."

  def validate(%{actor_id: actor, tenant_id: tenant})
      when is_binary(actor) and actor != "" and is_binary(tenant) and tenant != "", do: :ok

  def validate(_), do: {:error, :missing_actor_tenant_context}
end
