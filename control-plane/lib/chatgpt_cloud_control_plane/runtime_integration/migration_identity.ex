defmodule ChatGPTCloud.RuntimeIntegration.MigrationIdentity do
  @moduledoc "Binds schema migrations to exact source identity for replay."

  @spec digest([String.t()]) :: String.t()
  def digest(paths) when is_list(paths) do
    paths
    |> Enum.sort()
    |> Enum.join("\n")
    |> then(&:crypto.hash(:sha256, &1))
    |> Base.encode16(case: :lower)
  end
end
