defmodule ChatGPTCloudControlPlane.RuntimeContracts.AiToolScope do
  @moduledoc "Restricts AI-exposed actions to bounded read/query operations."
  @allowed [:read, :query, :explain]
  def validate(action) when action in @allowed, do: :ok
  def validate(_), do: {:error, :ai_actuation_refused}
end
