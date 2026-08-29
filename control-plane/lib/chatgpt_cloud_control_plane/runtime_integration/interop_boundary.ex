defmodule ChatGPTCloud.RuntimeIntegration.InteropBoundary do
  @moduledoc "Consumer-side interop contract that cannot acquire ambient consequential authority."
  @enforce_keys [:protocol, :producer, :consumer]
  defstruct [:protocol, :producer, :consumer, authority: :observe]

  @spec admissible?(struct()) :: boolean()
  def admissible?(%__MODULE__{authority: authority}), do: authority in [:observe, :construct]
end
