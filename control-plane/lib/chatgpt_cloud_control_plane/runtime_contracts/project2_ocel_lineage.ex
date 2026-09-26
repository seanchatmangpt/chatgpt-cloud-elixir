defmodule ChatGPTCloudControlPlane.RuntimeContracts.Project2OcelLineage do
  @moduledoc "Binds each runtime invocation to Project #2 and canonical GGen OCEL lineage."

  def validate(%{project: 2, ocel_key: "ggen/ecosystem/ocel/current", ocel_digest: digest})
      when is_binary(digest) and digest != "", do: :ok

  def validate(_), do: {:error, :invalid_project2_ocel_lineage}
end
