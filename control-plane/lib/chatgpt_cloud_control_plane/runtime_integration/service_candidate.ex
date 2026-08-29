defmodule ChatGPTCloud.RuntimeIntegration.ServiceCandidate do
  @moduledoc "Provider-neutral candidate for an abstract runtime service requirement."
  @enforce_keys [:capability, :provider]
  defstruct [:capability, :provider, constraints: %{}]

  @spec compatible?(struct(), map()) :: boolean()
  def compatible?(%__MODULE__{constraints: constraints}, observation) do
    Enum.all?(constraints, fn {key, value} -> Map.get(observation, key) == value end)
  end
end
