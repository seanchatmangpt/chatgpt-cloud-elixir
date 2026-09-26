defmodule ChatGPTCloudControlPlane.RuntimeContracts.RuntimeEnvironmentIdentity do
  @moduledoc "Binds execution evidence to OS, architecture, runtime, and environment identity."

  @required ~w(os arch runtime environment)a

  def validate(identity) when is_map(identity) do
    case Enum.find(@required, &(Map.get(identity, &1) in [nil, ""])) do
      nil -> :ok
      field -> {:error, {:missing_runtime_environment_identity, field}}
    end
  end

  def validate(_), do: {:error, :invalid_runtime_environment_identity}
end
