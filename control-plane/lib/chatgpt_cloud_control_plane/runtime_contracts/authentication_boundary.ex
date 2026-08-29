defmodule ChatGPTCloudControlPlane.RuntimeContracts.AuthenticationBoundary do
  @moduledoc "Separates operator-session authentication from agent-token authentication."

  def admit(%{actor: :operator, mechanism: mechanism}) when mechanism in [:password, :magic_link, :session], do: :ok
  def admit(%{actor: :agent, mechanism: :api_token}), do: :ok
  def admit(%{actor: actor, mechanism: mechanism}), do: {:error, {:invalid_authentication_boundary, actor, mechanism}}
  def admit(_), do: {:error, :invalid_authentication_context}
end
