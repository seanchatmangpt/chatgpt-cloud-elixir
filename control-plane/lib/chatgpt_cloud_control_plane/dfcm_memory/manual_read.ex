defmodule ChatGPTCloud.DfcmMemory.ManualRead do
  @moduledoc """
  Manual `:read` implementation for `ChatGPTCloud.DfcmMemory.MemoryRecord`, per
  the "wrap external APIs" pattern (https://ash.hexdocs.pm/wrap-external-apis.html):
  call the external API, transform results into resource structs, then let Ash
  apply the query's filter/sort/limit on the resulting in-memory list.
  """

  use Ash.Resource.ManualRead

  alias ChatGPTCloud.DfcmMemory.GithubProjectClient
  alias ChatGPTCloud.DfcmMemory.MemoryRecord

  @impl true
  def read(ash_query, _ecto_query, _opts, _context) do
    include_archived = ash_query.context[:include_archived] || false

    case GithubProjectClient.memory_items(include_archived) do
      {:ok, {records, _truncated}} ->
        structs = Enum.map(records, &to_struct/1)
        Ash.Query.apply_to(ash_query, structs)

      {:error, error} ->
        {:error, error}
    end
  end

  defp to_struct(record) do
    meta = record.metadata || %{}

    struct(MemoryRecord, %{
      key: meta["key"],
      title: record.title,
      kind: meta["kind"],
      cell: meta["cell"],
      standing: meta["standing"],
      tags: meta["tags"] || [],
      body: record.body,
      metadata: meta,
      item_id: record.item_id,
      content_id: record.content_id,
      is_archived: record.is_archived,
      updated_at: meta["updated_at"]
    })
  end
end
