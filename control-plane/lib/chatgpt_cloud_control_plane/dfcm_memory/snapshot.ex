defmodule ChatGPTCloud.DfcmMemory.Snapshot do
  @moduledoc "Generic-action implementation backing `MemoryRecord.snapshot/0`."

  use Ash.Resource.Actions.Implementation

  alias ChatGPTCloud.DfcmMemory.GithubProjectClient

  @impl true
  def run(_input, _opts, _context) do
    case GithubProjectClient.snapshot() do
      {:ok, result} ->
        {:ok, result}

      {:error, %{message: message, standing: standing, reason: reason}} ->
        {:error, Ash.Error.to_ash_error("#{standing}[#{reason}]: #{message}")}

      {:error, other} ->
        {:error, Ash.Error.to_ash_error(inspect(other))}
    end
  end
end
