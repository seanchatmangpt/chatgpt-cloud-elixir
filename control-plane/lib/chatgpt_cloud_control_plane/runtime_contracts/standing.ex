defmodule ChatGPTCloudControlPlane.RuntimeContracts.Standing do
  @moduledoc "Keeps runtime standing inside the repository evidence vocabulary."
  @allowed [:unknown, :partial_alive, :alive, :blocked, :build_broken, :unsupported, :refused]
  def validate(value) when value in @allowed, do: :ok
  def validate(value), do: {:error, {:invalid_standing, value}}
end
