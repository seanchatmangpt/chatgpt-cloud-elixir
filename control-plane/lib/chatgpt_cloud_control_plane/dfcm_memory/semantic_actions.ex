defmodule ChatGPTCloud.DfcmMemory.SemanticAction do
  @moduledoc false

  alias ChatGPTCloud.DfcmMemory.{VirtualProject, Vision2030}

  def run(input, view) do
    max_items = Ash.ActionInput.get_argument(input, :max_items)
    include_archived = Ash.ActionInput.get_argument(input, :include_archived)
    include_bodies = Ash.ActionInput.get_argument(input, :include_bodies)
    types = Ash.ActionInput.get_argument(input, :types)
    query = Ash.ActionInput.get_argument(input, :query) || %{}

    opts =
      [
        max_items: max_items,
        include_archived: include_archived,
        include_bodies: include_bodies,
        types: types
      ]
      |> Enum.reject(fn {_key, value} -> is_nil(value) end)

    case VirtualProject.project(opts) do
      {:ok, graph} ->
        result =
          case view do
            "vision2030" -> Vision2030.project(graph, query)
            _ -> VirtualProject.view(graph, view, query)
          end

        case result do
          {:error, reason} -> {:error, Ash.Error.to_ash_error(reason)}
          projection -> {:ok, projection}
        end

      {:error, %{message: message, standing: standing, reason: reason}} ->
        {:error, Ash.Error.to_ash_error("#{standing}[#{reason}]: #{message}")}

      {:error, other} ->
        {:error, Ash.Error.to_ash_error(inspect(other))}
    end
  end

  def run_semantic(input) do
    max_items = Ash.ActionInput.get_argument(input, :max_items)
    include_archived = Ash.ActionInput.get_argument(input, :include_archived)
    include_bodies = Ash.ActionInput.get_argument(input, :include_bodies)
    types = Ash.ActionInput.get_argument(input, :types)
    views = Ash.ActionInput.get_argument(input, :views)
    query = Ash.ActionInput.get_argument(input, :query) || %{}

    opts =
      [
        max_items: max_items,
        include_archived: include_archived,
        include_bodies: include_bodies,
        types: types
      ]
      |> Enum.reject(fn {_key, value} -> is_nil(value) end)

    case VirtualProject.project(opts) do
      {:ok, graph} ->
        case VirtualProject.semantic(graph, views, query) do
          {:error, reason} -> {:error, Ash.Error.to_ash_error(reason)}
          result -> {:ok, result}
        end

      {:error, %{message: message, standing: standing, reason: reason}} ->
        {:error, Ash.Error.to_ash_error("#{standing}[#{reason}]: #{message}")}

      {:error, other} ->
        {:error, Ash.Error.to_ash_error(inspect(other))}
    end
  end
end

defmodule ChatGPTCloud.DfcmMemory.SemanticBundle do
  use Ash.Resource.Actions.Implementation
  @impl true
  def run(input, _opts, _context), do: ChatGPTCloud.DfcmMemory.SemanticAction.run_semantic(input)
end

defmodule ChatGPTCloud.DfcmMemory.SemanticGraph do
  use Ash.Resource.Actions.Implementation
  @impl true
  def run(input, _opts, _context), do: ChatGPTCloud.DfcmMemory.SemanticAction.run(input, "graph")
end

defmodule ChatGPTCloud.DfcmMemory.SemanticGraphQuery do
  use Ash.Resource.Actions.Implementation
  @impl true
  def run(input, _opts, _context), do: ChatGPTCloud.DfcmMemory.SemanticAction.run(input, "query")
end

defmodule ChatGPTCloud.DfcmMemory.SemanticTables do
  use Ash.Resource.Actions.Implementation
  @impl true
  def run(input, _opts, _context), do: ChatGPTCloud.DfcmMemory.SemanticAction.run(input, "tables")
end

defmodule ChatGPTCloud.DfcmMemory.SemanticTriples do
  use Ash.Resource.Actions.Implementation
  @impl true
  def run(input, _opts, _context),
    do: ChatGPTCloud.DfcmMemory.SemanticAction.run(input, "triples")
end

defmodule ChatGPTCloud.DfcmMemory.SemanticJsonLd do
  use Ash.Resource.Actions.Implementation
  @impl true
  def run(input, _opts, _context), do: ChatGPTCloud.DfcmMemory.SemanticAction.run(input, "jsonld")
end

defmodule ChatGPTCloud.DfcmMemory.SemanticServices do
  use Ash.Resource.Actions.Implementation
  @impl true
  def run(input, _opts, _context),
    do: ChatGPTCloud.DfcmMemory.SemanticAction.run(input, "services")
end

defmodule ChatGPTCloud.DfcmMemory.SemanticOcel do
  use Ash.Resource.Actions.Implementation
  @impl true
  def run(input, _opts, _context), do: ChatGPTCloud.DfcmMemory.SemanticAction.run(input, "ocel")
end

defmodule ChatGPTCloud.DfcmMemory.SemanticContext do
  use Ash.Resource.Actions.Implementation
  @impl true
  def run(input, _opts, _context),
    do: ChatGPTCloud.DfcmMemory.SemanticAction.run(input, "context")
end

defmodule ChatGPTCloud.DfcmMemory.SemanticVision2030 do
  use Ash.Resource.Actions.Implementation
  @impl true
  def run(input, _opts, _context),
    do: ChatGPTCloud.DfcmMemory.SemanticAction.run(input, "vision2030")
end
