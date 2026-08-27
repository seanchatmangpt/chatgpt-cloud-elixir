defmodule ChatGPTCloudControlPlane.RuntimeContracts.SparkExtensionContract do
  @moduledoc "Validates compile-time extension wiring for standing, authority, and runtime ownership."

  @domains [:standing, :authority, :runtime, :integration]

  def validate(%{domain: domain, module: module}) when domain in @domains and is_atom(module), do: :ok
  def validate(%{domain: domain}), do: {:error, {:invalid_spark_domain, domain}}
  def validate(_), do: {:error, :invalid_spark_extension}
end
