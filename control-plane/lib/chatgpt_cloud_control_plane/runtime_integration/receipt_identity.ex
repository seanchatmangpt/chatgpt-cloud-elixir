defmodule ChatGPTCloud.RuntimeIntegration.ReceiptIdentity do
  @moduledoc "Deterministic receipt identity for exact runtime observations."

  @spec digest(map()) :: String.t()
  def digest(fields) when is_map(fields) do
    fields
    |> Enum.sort()
    |> :erlang.term_to_binary([:deterministic])
    |> then(&:crypto.hash(:sha256, &1))
    |> Base.encode16(case: :lower)
  end
end
