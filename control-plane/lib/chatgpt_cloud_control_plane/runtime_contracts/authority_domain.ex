defmodule ChatGPTCloudControlPlane.RuntimeContracts.AuthorityDomain do
  @moduledoc "Requires actions to remain inside an explicitly admitted authority domain."
  def validate(domain, admitted) when is_atom(domain) and is_list(admitted) do
    if domain in admitted, do: :ok, else: {:error, {:authority_domain_refused, domain}}
  end
  def validate(_, _), do: {:error, :invalid_authority_domain}
end
