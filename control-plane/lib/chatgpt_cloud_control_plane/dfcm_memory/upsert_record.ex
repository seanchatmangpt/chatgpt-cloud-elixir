defmodule ChatGPTCloud.DfcmMemory.UpsertRecord do
  @moduledoc """
  Generic-action implementation backing `MemoryRecord.upsert_record/1`. This is
  the write half of the read-before-manufacture / write-after-manufacture
  contract in `project-memory/README.md`: it always resolves the current record
  for `key` first (so an update never blind-overwrites), then creates or
  updates the corresponding Project draft issue.
  """

  use Ash.Resource.Actions.Implementation

  alias ChatGPTCloud.DfcmMemory.GithubProjectClient

  @impl true
  def run(input, _opts, _context) do
    record =
      input.arguments
      |> Map.take([:key, :title, :kind, :cell, :standing, :tags, :body, :metadata])
      |> Enum.reject(fn {_k, v} -> is_nil(v) end)
      |> Map.new(fn {k, v} -> {to_string(k), v} end)
      |> then(fn base ->
        metadata = Map.get(base, "metadata", %{})

        base
        |> Map.merge(metadata)
        |> Map.drop(["metadata"])
      end)

    case GithubProjectClient.upsert(record) do
      {:ok, result} -> {:ok, result}
      {:error, %{message: message, standing: standing, reason: reason}} ->
        {:error, Ash.Error.to_ash_error("#{standing}[#{reason}]: #{message}")}

      {:error, other} ->
        {:error, Ash.Error.to_ash_error(inspect(other))}
    end
  end
end
