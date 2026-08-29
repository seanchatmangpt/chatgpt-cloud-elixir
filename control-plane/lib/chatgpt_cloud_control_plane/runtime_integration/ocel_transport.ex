defmodule ChatGPTCloud.RuntimeIntegration.OcelTransport do
  @moduledoc "Versioned observational OCEL ingestion contract."
  @schema "chatgpt-cloud-ocel/1"

  @spec admit(map()) :: :ok | {:error, :invalid_ocel_envelope}
  def admit(%{"schema" => @schema, "events" => events}) when is_list(events), do: :ok
  def admit(%{schema: @schema, events: events}) when is_list(events), do: :ok
  def admit(_), do: {:error, :invalid_ocel_envelope}
end
