defmodule ChatGPTCloudControlPlane.RuntimeContracts.SessionExpiryGuard do
  @moduledoc "Rejects expired operator sessions before runtime actions are admitted."

  def admit(%{expires_at: %DateTime{} = expires_at}, now \\ DateTime.utc_now()) do
    if DateTime.compare(expires_at, now) == :gt, do: :ok, else: {:error, :operator_session_expired}
  end

  def admit(_, _), do: {:error, :invalid_session_expiry}
end
