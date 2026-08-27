defmodule ChatGPTCloudControlPlane.RuntimeContracts.AdminSurfaceGuard do
  @moduledoc "Restricts AshAdmin write surfaces to authenticated operator roles."

  def admit(%{mode: :read}), do: :ok
  def admit(%{mode: :write, role: role}) when role in [:operator, :admin], do: :ok
  def admit(%{mode: :write}), do: {:error, :admin_write_requires_operator_role}
  def admit(_), do: {:error, :invalid_admin_surface_request}
end
