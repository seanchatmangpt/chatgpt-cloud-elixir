defmodule ChatGPTCloud.RuntimeIntegration.ActionAuthorityMatrix do
  @moduledoc """Explicit SELECT/CONSTRUCT/DO authority admission for runtime operation classes."""

  @matrix %{
    read: [:select, :construct, :do],
    ingest: [:construct, :do],
    qualify: [:construct, :do],
    replay: [:construct, :do],
    archive: [:construct, :do],
    deploy: [:do]
  }

  @spec admit(atom(), atom()) :: :ok | {:error, :authority_refused}
  def admit(operation, authority) do
    if authority in Map.get(@matrix, operation, []), do: :ok, else: {:error, :authority_refused}
  end

  @spec permitted(atom()) :: [atom()]
  def permitted(operation), do: Map.get(@matrix, operation, [])
end
