defmodule ChatGPTCloud.RuntimeIntegration.WorkerReceipt do
  @moduledoc "Durable worker receipt binding queue, attempt, idempotency, and result."
  @enforce_keys [:queue, :attempt, :idempotency_key, :result]
  defstruct [:queue, :attempt, :idempotency_key, :result]

  @spec successful?(struct()) :: boolean()
  def successful?(%__MODULE__{result: :ok}), do: true
  def successful?(%__MODULE__{}), do: false
end
