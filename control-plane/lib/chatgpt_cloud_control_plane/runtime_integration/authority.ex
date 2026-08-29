defmodule ChatGPTCloud.RuntimeIntegration.Authority do
  @moduledoc "Separates SELECT, CONSTRUCT, and consequential DO authority."
  @type domain :: :select | :construct | :do

  @spec granted?(map(), domain()) :: boolean()
  def granted?(authority, domain) when domain in [:select, :construct, :do],
    do: Map.get(authority, domain, false) == true

  @spec require_do(map()) :: :ok | {:error, :do_authority_required}
  def require_do(authority),
    do: if(granted?(authority, :do), do: :ok, else: {:error, :do_authority_required})
end
