defmodule ChatGPTCloud.RuntimeIntegration.OcelIngestionContract do
  @moduledoc """Versioned OCEL ingestion contract whose transport remains observational."""

  @enforce_keys [:protocol_version, :producer, :event_id]
  defstruct [:protocol_version, :producer, :event_id, authority: :observe]

  @type t :: %__MODULE__{
          protocol_version: String.t(),
          producer: String.t(),
          event_id: String.t(),
          authority: atom()
        }

  @spec admit(t()) :: :ok | {:error, atom()}
  def admit(%__MODULE__{protocol_version: version, producer: producer, event_id: event_id, authority: :observe})
      when is_binary(version) and version != "" and producer in ["ex4pm", "ash_r2rml", "wasm4pm"] and
             is_binary(event_id) and event_id != "",
      do: :ok

  def admit(%__MODULE__{authority: _}), do: {:error, :transport_actuation_refused}
  def admit(_), do: {:error, :invalid_ocel_ingestion_contract}
end
