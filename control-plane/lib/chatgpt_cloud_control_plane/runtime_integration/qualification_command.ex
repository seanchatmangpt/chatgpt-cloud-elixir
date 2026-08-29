defmodule ChatGPTCloud.RuntimeIntegration.QualificationCommand do
  @moduledoc "Ordered exact-head qualification ladder for the control plane."
  @commands [
    "mix format --check-formatted",
    "MIX_ENV=test mix compile --warnings-as-errors",
    "MIX_ENV=test mix ecto.create --quiet",
    "MIX_ENV=test mix ecto.migrate --quiet",
    "MIX_ENV=test mix test"
  ]

  @spec commands() :: [String.t()]
  def commands, do: @commands
end
