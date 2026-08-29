defmodule ChatGPTCloudControlPlane.RuntimeContracts.ReactorContract do
  @moduledoc "Requires Reactor workflows to expose steps, rollback policy, and receipt identity."
  def validate(%{steps: steps, rollback: rollback, receipt_id: id}) when is_list(steps) and steps != [] and rollback in [:required, :best_effort, :none] and is_binary(id) and id != "", do: :ok
  def validate(_), do: {:error, :reactor_contract_incomplete}
end
