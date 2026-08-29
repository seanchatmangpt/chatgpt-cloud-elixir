defmodule ChatGPTCloud.RuntimeIntegration.ArchivalPolicy do
  @moduledoc "Preserves process evidence by requiring archive semantics instead of hard delete."

  @spec disposition(atom()) :: :archive | :retain
  def disposition(kind) when kind in [:receipt, :event, :qualification, :refusal], do: :archive
  def disposition(_), do: :retain
end
