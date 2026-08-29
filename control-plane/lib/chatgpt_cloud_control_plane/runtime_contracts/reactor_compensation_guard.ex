defmodule ChatGPTCloudControlPlane.RuntimeContracts.ReactorCompensationGuard do
  @moduledoc "Requires compensation to bind to the failed Reactor step and original receipt."

  def validate(%{failed_step: step, receipt_digest: digest, compensating_action: action})
      when is_binary(step) and step != "" and is_binary(digest) and digest != "" and is_atom(action), do: :ok

  def validate(_), do: {:error, :invalid_compensation_contract}
end
