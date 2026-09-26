defmodule ChatGPTCloudControlPlane.RuntimeContracts.OcelTransportStandingGuard do
  @moduledoc "Prevents observational OCEL transport from upgrading or downgrading subject qualification."

  def apply_transport(standing, %{protocol: protocol}) when protocol in ["ocel/2.0", "ggen/ecosystem/ocel/current"], do: {:ok, standing}
  def apply_transport(_, _), do: {:error, :invalid_ocel_transport}
end
