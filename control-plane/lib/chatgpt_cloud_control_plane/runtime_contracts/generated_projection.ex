defmodule ChatGPTCloudControlPlane.RuntimeContracts.GeneratedProjection do
  @moduledoc "Refuses direct mutation of generated runtime projections."
  def validate(%{generated: true, mutation: :direct}), do: {:error, :generated_projection_mutation_refused}
  def validate(%{generated: true, mutation: :regenerate}), do: :ok
  def validate(%{generated: false}), do: :ok
  def validate(_), do: {:error, :invalid_projection_contract}
end
