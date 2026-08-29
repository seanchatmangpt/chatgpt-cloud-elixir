defmodule ChatGPTCloudControlPlane.RuntimeContracts.RuntimeDependencyPin do
  @moduledoc "Requires runtime integration dependencies to be explicitly version-pinned."

  def validate(%{name: name, version: version}) when is_binary(name) and name != "" and is_binary(version) and version != "" do
    if String.contains?(version, [">", "<", "*", "x"]), do: {:error, {:floating_dependency, name, version}}, else: :ok
  end

  def validate(_), do: {:error, :invalid_dependency_pin}
end
