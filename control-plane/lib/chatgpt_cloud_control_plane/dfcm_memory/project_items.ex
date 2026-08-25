defmodule ChatGPTCloud.DfcmMemory.ProjectItems do
  @moduledoc "Generic-action implementation backing `MemoryRecord.project_items/0`."

  use Ash.Resource.Actions.Implementation

  alias ChatGPTCloud.DfcmMemory.GithubProjectClient

  @impl true
  def run(input, _opts, _context) do
    max_items = Ash.ActionInput.get_argument(input, :max_items)
    types = Ash.ActionInput.get_argument(input, :types)
    include_archived = Ash.ActionInput.get_argument(input, :include_archived)

    opts =
      [max_items: max_items, types: types, include_archived: include_archived]
      |> Enum.reject(fn {_k, v} -> is_nil(v) end)

    case GithubProjectClient.project_items(opts) do
      {:ok, result} ->
        {:ok, result}

      {:error, %{message: message, standing: standing, reason: reason}} ->
        {:error, Ash.Error.to_ash_error("#{standing}[#{reason}]: #{message}")}

      {:error, other} ->
        {:error, Ash.Error.to_ash_error(inspect(other))}
    end
  end
end
