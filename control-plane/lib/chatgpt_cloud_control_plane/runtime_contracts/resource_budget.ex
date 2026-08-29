defmodule ChatGPTCloudControlPlane.RuntimeContracts.ResourceBudget do
  @moduledoc "Requires bounded positive runtime resource budgets before consequential execution."

  def validate(%{cpu_ms: cpu, memory_bytes: memory})
      when is_integer(cpu) and cpu > 0 and is_integer(memory) and memory > 0, do: :ok

  def validate(_), do: {:error, :invalid_resource_budget}
end
