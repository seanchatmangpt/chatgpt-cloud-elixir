defmodule ChatGPTCloudControlPlane.RuntimeContracts.RuntimeInterop do
  @moduledoc "Requires provider-neutral interop identity at runtime boundaries."
  def validate(%{protocol: p, producer: a, consumer: b}) when is_binary(p) and p != "" and is_binary(a) and a != "" and is_binary(b) and b != "", do: :ok
  def validate(_), do: {:error, :runtime_interop_identity_missing}
end
