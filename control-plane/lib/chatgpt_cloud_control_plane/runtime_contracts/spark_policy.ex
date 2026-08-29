defmodule ChatGPTCloudControlPlane.RuntimeContracts.SparkPolicy do
  @moduledoc "Requires standing and authority domains on compile-time extension policy."
  def validate(%{standing_domain: s, authority_domain: a}) when is_atom(s) and is_atom(a), do: :ok
  def validate(_), do: {:error, :spark_policy_incomplete}
end
