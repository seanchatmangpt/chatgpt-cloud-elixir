defmodule ChatGPTCloud.Xaas.Capabilities do
  @moduledoc """
  Client-side mirror of the XaaS fabric allowlist. The fabric exposes exactly three
  capabilities; `actuate` (the DO verb) is refused by authority ceiling, permanently.
  Unknown verbs fail closed.
  """

  @allowlist ~w(fabric.probe run.submit epoch.receipts)

  def allowlist, do: @allowlist

  @spec admit(String.t()) ::
          :ok
          | {:refused, {:authority_ceiling, String.t()}}
          | {:refused, {:capability_not_admitted, String.t()}}
  def admit("actuate"), do: {:refused, {:authority_ceiling, "actuate"}}
  def admit(verb) when verb in @allowlist, do: :ok
  def admit(verb), do: {:refused, {:capability_not_admitted, to_string(verb)}}
end
