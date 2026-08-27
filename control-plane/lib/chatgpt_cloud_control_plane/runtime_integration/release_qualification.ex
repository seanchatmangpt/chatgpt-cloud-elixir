defmodule ChatGPTCloud.RuntimeIntegration.ReleaseQualification do
  @moduledoc "Requires compile, database, tests, release, and image gates before release standing can advance."
  @required [:compile, :migrate, :tests, :release, :image]

  @spec complete?(map()) :: boolean()
  def complete?(results) when is_map(results),
    do: Enum.all?(@required, &(Map.get(results, &1) == :ok))
end
