defmodule ChatGPTCloudControlPlane.RuntimeContracts.AshActionAuthority do
  @moduledoc "Separates Ash action selection/construction from consequential DO authority."

  def admit(%{phase: phase}) when phase in [:select, :construct], do: :ok
  def admit(%{phase: :do, authority: :brce}), do: :ok
  def admit(%{phase: :do}), do: {:error, :ash_action_do_requires_brce}
  def admit(_), do: {:error, :invalid_ash_action_phase}
end
