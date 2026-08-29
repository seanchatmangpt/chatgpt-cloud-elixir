defmodule ChatGPTCloudControlPlane.RuntimeContracts.AiToolAuthorityGuard do
  @moduledoc "Limits AshAI tools to bounded reads and intent construction; production DO is refused."

  def admit(%{operation: op}) when op in [:read, :query, :construct_intent], do: :ok
  def admit(%{operation: op}) when op in [:deploy, :release, :cutover, :bill], do: {:error, {:ai_tool_do_refused, op}}
  def admit(_), do: {:error, :invalid_ai_tool_operation}
end
