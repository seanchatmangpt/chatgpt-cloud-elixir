defmodule ChatGPTCloud.RuntimeIntegration.ApiOperationAdmission do
  @moduledoc """Admission boundary joining declared machine projections with caller authority."""

  alias ChatGPTCloud.RuntimeIntegration.ApiProjectionContract

  @spec admit(ApiProjectionContract.t(), atom(), atom()) :: :ok | {:error, atom()}
  def admit(%ApiProjectionContract{} = contract, operation, authority) do
    cond do
      not ApiProjectionContract.valid?(contract) -> {:error, :invalid_api_projection}
      operation not in contract.operations -> {:error, :operation_not_projected}
      ApiProjectionContract.mutation?(operation) and authority not in [:construct, :do] -> {:error, :mutation_authority_required}
      true -> :ok
    end
  end
end
