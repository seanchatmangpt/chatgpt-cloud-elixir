defmodule ChatGPTCloudControlPlane.RuntimeContracts.IdempotencyKey do
  @moduledoc "Requires stable idempotency identity for ingestion and replay actions."

  def validate(key) when is_binary(key) and byte_size(key) >= 16, do: :ok
  def validate(_), do: {:error, :missing_or_weak_idempotency_key}
end
