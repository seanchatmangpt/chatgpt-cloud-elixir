defmodule ChatGPTCloudControlPlane.RuntimeContracts.Compensation do
  @moduledoc "Keeps Reactor compensation explicit and authority-bounded."

  def validate(%{required: true, authority_ref: ref}) when is_binary(ref) and ref != "", do: :ok
  def validate(%{required: false}), do: :ok
  def validate(%{required: true}), do: {:error, :compensation_authority_missing}
  def validate(_), do: {:error, :invalid_compensation_contract}
end
