defmodule ChatGPTCloud.RuntimeIntegration.ReadProjection do
  @moduledoc "Projects only explicitly admitted fields to machine/read interfaces."

  @spec project(map(), [atom() | String.t()]) :: map()
  def project(record, allowed) when is_map(record) and is_list(allowed), do: Map.take(record, allowed)
end
