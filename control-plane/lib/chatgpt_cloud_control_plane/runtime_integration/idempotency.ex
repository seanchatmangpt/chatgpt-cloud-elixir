defmodule ChatGPTCloud.RuntimeIntegration.Idempotency do
  @moduledoc "Content-derived idempotency keys for runtime actions."

  @spec key(String.t(), map()) :: String.t()
  def key(operation, input) when is_binary(operation) and is_map(input) do
    %{operation: operation, input: input}
    |> :erlang.term_to_binary([:deterministic])
    |> then(&:crypto.hash(:sha256, &1))
    |> Base.url_encode64(padding: false)
  end
end
