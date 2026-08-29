defmodule ChatGPTCloudControlPlane.RuntimeContracts.RefusalEnvelope do
  @moduledoc "Represents typed runtime refusal separately from transport or execution failure."

  def build(type, reason) when is_atom(type) and is_binary(reason) and reason != "" do
    {:ok, %{standing: :REFUSED_TYPED, type: type, reason: reason, actuated: false}}
  end

  def build(_, _), do: {:error, :invalid_refusal_envelope}
end
