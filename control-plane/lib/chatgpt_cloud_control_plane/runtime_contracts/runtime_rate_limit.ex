defmodule ChatGPTCloudControlPlane.RuntimeContracts.RuntimeRateLimit do
  @moduledoc "Maps positive finite runtime rate limits to the governed adapter capability contract."

  def validate(%{limit: limit, interval_ms: interval}) when is_integer(limit) and limit > 0 and is_integer(interval) and interval > 0, do: :ok
  def validate(_), do: {:error, :invalid_runtime_rate_limit}
end
