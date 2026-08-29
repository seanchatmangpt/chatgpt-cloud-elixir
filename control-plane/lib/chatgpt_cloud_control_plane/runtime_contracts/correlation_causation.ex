defmodule ChatGPTCloudControlPlane.RuntimeContracts.CorrelationCausation do
  @moduledoc "Preserves distributed invocation lineage with explicit correlation and causation IDs."

  def validate(%{correlation_id: correlation, causation_id: causation})
      when is_binary(correlation) and correlation != "" and is_binary(causation) and causation != "", do: :ok

  def validate(_), do: {:error, :missing_correlation_causation}
end
