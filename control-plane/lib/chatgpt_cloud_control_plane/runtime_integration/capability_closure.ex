defmodule ChatGPTCloud.RuntimeIntegration.CapabilityClosure do
  @moduledoc "Deterministic transitive closure for runtime capability dependencies."

  @spec resolve([atom()], map()) :: [atom()]
  def resolve(roots, graph) do
    roots
    |> Enum.reduce(MapSet.new(), &visit(&1, graph, &2))
    |> MapSet.to_list()
    |> Enum.sort()
  end

  defp visit(node, graph, seen) do
    if MapSet.member?(seen, node) do
      seen
    else
      Enum.reduce(Map.get(graph, node, []), MapSet.put(seen, node), &visit(&1, graph, &2))
    end
  end
end
