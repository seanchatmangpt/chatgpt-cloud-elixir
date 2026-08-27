defmodule ChatGPTCloudControlPlane.RuntimeContracts.RetryPolicy do
  @moduledoc "Bounds retry count and delay so asynchronous work cannot retry implicitly forever."
  def validate(%{max_attempts: a, backoff_ms: b}) when is_integer(a) and a > 0 and a <= 25 and is_integer(b) and b >= 0, do: :ok
  def validate(_), do: {:error, :invalid_retry_policy}
end
