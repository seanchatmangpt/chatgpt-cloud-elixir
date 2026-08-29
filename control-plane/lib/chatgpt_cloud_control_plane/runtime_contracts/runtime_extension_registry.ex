defmodule ChatGPTCloudControlPlane.RuntimeContracts.RuntimeExtensionRegistry do
  @moduledoc "Validates unique extension ownership across the admitted Ash runtime ecosystem."

  def validate(entries) when is_list(entries) do
    names = Enum.map(entries, &Map.get(&1, :name))
    cond do
      Enum.any?(names, &(&1 in [nil, ""])) -> {:error, :unnamed_runtime_extension}
      length(names) != length(Enum.uniq(names)) -> {:error, :duplicate_runtime_extension}
      true -> :ok
    end
  end

  def validate(_), do: {:error, :invalid_extension_registry}
end
