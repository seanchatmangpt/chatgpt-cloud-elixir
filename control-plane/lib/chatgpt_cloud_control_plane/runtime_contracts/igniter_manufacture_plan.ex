defmodule ChatGPTCloudControlPlane.RuntimeContracts.IgniterManufacturePlan do
  @moduledoc "Binds reproducible ecosystem manufacture to explicit package, version, and verifier steps."

  def validate(%{packages: packages, verifier: verifier}) when is_list(packages) and packages != [] and is_binary(verifier) and verifier != "" do
    if Enum.all?(packages, &valid_package?/1), do: :ok, else: {:error, :unpinned_igniter_package}
  end

  def validate(_), do: {:error, :invalid_igniter_plan}

  defp valid_package?(%{name: name, version: version}), do: is_binary(name) and name != "" and is_binary(version) and version != ""
  defp valid_package?(_), do: false
end
