defmodule ChatGPTCloud.RuntimeIntegration.ReactorExecutionPlan do
  @moduledoc """Ordered runtime orchestration plan for ingestion, conformance, qualification and replay."""

  @allowed [:ingest, :conform, :qualify, :replay]
  @enforce_keys [:steps]
  defstruct [:steps]

  @spec admit(t()) :: :ok | {:error, :invalid_reactor_plan} when t: %__MODULE__{}
  def admit(%__MODULE__{steps: steps}) when is_list(steps) and steps != [] do
    if Enum.all?(steps, &(&1 in @allowed)) and length(steps) == length(Enum.uniq(steps)), do: :ok, else: {:error, :invalid_reactor_plan}
  end

  def admit(_), do: {:error, :invalid_reactor_plan}
end
