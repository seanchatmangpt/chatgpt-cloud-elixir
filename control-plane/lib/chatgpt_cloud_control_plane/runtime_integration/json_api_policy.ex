defmodule ChatGPTCloud.RuntimeIntegration.JsonApiPolicy do
  @moduledoc "Admits only explicitly projected JSON:API actions."

  @spec admit(atom(), [atom()]) :: :ok | {:error, :json_api_action_not_projected}
  def admit(action, projected) when is_list(projected),
    do: if(action in projected, do: :ok, else: {:error, :json_api_action_not_projected})
end
