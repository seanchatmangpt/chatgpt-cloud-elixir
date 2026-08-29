defmodule ChatGPTCloudControlPlane.RuntimeContracts.StandingEvidenceLadder do
  @moduledoc "Maps evidence classes to the strongest standing they may lawfully support."

  def strongest(:inspection), do: :UNKNOWN
  def strongest(:construction), do: :PARTIAL_ALIVE
  def strongest(:exact_execution_success), do: :ALIVE
  def strongest(:exact_execution_failure), do: :BUILD_BROKEN
  def strongest(:authority_boundary), do: :BLOCKED
  def strongest(_), do: :UNSUPPORTED
end
