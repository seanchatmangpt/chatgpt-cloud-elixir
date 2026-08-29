defmodule ChatGPTCloud.RuntimeIntegration.AiToolPolicy do
  @moduledoc "Bounds AshAI exposure to explicitly read-only runtime actions."
  @read_actions MapSet.new([:read, :list, :get, :inspect, :query])

  @spec admit(atom()) :: :ok | {:error, :ai_actuation_forbidden}
  def admit(action),
    do:
      if(MapSet.member?(@read_actions, action), do: :ok, else: {:error, :ai_actuation_forbidden})
end
