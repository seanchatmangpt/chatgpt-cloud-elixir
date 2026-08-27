defmodule ChatGPTCloud.RuntimeIntegration.IgniterPlan do
  @moduledoc "Deterministic ecosystem manufacture plan for Igniter-driven setup."
  @extensions [
    :spark,
    :reactor,
    :ash_json_api,
    :ash_authentication,
    :ash_oban,
    :ash_state_machine,
    :ash_archival,
    :ash_money,
    :ash_cloak,
    :ash_graphql,
    :ash_ai
  ]

  @spec extensions() :: [atom()]
  def extensions, do: @extensions

  @spec fingerprint() :: String.t()
  def fingerprint do
    @extensions |> Enum.map_join("\n", &Atom.to_string/1) |> then(&:crypto.hash(:sha256, &1)) |> Base.encode16(case: :lower)
  end
end
