defmodule ChatGPTCloud.RuntimeIntegration.RuntimeIntegrationAcceptance do
  @moduledoc """Exact-subject acceptance gate for the Ash-native runtime integration surface."""

  alias ChatGPTCloud.RuntimeIntegration.{QualificationStanding, RuntimeIntegrationPlan}

  @spec evaluate(RuntimeIntegrationPlan.t(), String.t(), map()) :: :alive | :unknown | :build_broken | {:error, term()}
  def evaluate(%RuntimeIntegrationPlan{} = plan, subject_sha, execution) do
    with :ok <- RuntimeIntegrationPlan.admit(plan) do
      QualificationStanding.derive(subject_sha, execution)
    end
  end
end
