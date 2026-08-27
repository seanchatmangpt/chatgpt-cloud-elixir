defmodule ChatGPTCloud.RuntimeIntegration do
  @moduledoc "Admission façade for exact-subject Ash runtime integration work."

  alias ChatGPTCloud.RuntimeIntegration.{
    CapabilityAdmission,
    ExactSubject,
    SparkContract
  }

  @spec admit(map()) :: {:ok, ExactSubject.t() | struct()} | {:error, term()}
  def admit(%{
        repository: repository,
        ref: ref,
        sha: sha,
        required_capabilities: required,
        available_capabilities: available,
        extensions: extensions
      }) do
    with {:ok, subject} <- ExactSubject.new(repository, ref, sha),
         :ok <- CapabilityAdmission.admit(required, available),
         :ok <- SparkContract.verify(extensions) do
      {:ok, subject}
    end
  end
end
