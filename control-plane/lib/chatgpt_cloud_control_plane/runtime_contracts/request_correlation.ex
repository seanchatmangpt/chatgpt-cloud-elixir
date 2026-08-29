defmodule ChatGPTCloudControlPlane.RuntimeContracts.RequestCorrelation do
  @moduledoc "Binds machine API requests, runtime actions, and receipts through a stable correlation identity."

  def validate(%{request_id: request, action_id: action, receipt_id: receipt})
      when is_binary(request) and request != "" and is_binary(action) and action != "" and is_binary(receipt) and receipt != "", do: :ok

  def validate(_), do: {:error, :invalid_request_correlation}
end
