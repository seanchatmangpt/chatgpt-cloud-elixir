defmodule ChatGPTCloudControlPlane.RuntimeContracts.AshAction do
  @moduledoc "Requires Ash runtime actions to declare resource, action, subject and authority identity."
  def validate(%{resource: r, action: a, subject: s, authority_ref: ref}) when is_atom(r) and is_atom(a) and is_map(s) and is_binary(ref) and ref != "", do: :ok
  def validate(_), do: {:error, :ash_action_contract_incomplete}
end
