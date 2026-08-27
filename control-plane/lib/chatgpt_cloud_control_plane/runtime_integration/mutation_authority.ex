defmodule ChatGPTCloud.RuntimeIntegration.MutationAuthority do
  @moduledoc "Requires authenticated identity plus explicit construction authority for mutations."

  @spec admit(map(), map()) :: :ok | {:error, atom()}
  def admit(%{principal: principal}, %{construct: true})
      when is_binary(principal) and byte_size(principal) > 0, do: :ok

  def admit(%{}, %{construct: false}), do: {:error, :construct_authority_required}
  def admit(_, _), do: {:error, :authenticated_principal_required}
end
