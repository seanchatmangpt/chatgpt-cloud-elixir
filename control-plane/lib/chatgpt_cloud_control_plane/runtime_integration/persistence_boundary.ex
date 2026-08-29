defmodule ChatGPTCloud.RuntimeIntegration.PersistenceBoundary do
  @moduledoc "Declares which runtime artifacts require durable persistence."
  @durable MapSet.new([
             :run,
             :receipt,
             :qualification,
             :refusal,
             :event,
             :object,
             :cost_observation
           ])

  @spec durable?(atom()) :: boolean()
  def durable?(kind), do: MapSet.member?(@durable, kind)
end
