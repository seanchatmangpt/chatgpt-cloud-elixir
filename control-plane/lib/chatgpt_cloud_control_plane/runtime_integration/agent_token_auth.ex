defmodule ChatGPTCloud.RuntimeIntegration.AgentTokenAuth do
  @moduledoc "Separate API-token boundary for machine ingestion clients."

  @spec verify(String.t() | nil, String.t() | nil) :: :ok | {:error, :invalid_agent_token}
  def verify(provided, expected) when is_binary(provided) and is_binary(expected) do
    if byte_size(provided) == byte_size(expected) and
         Plug.Crypto.secure_compare(provided, expected),
       do: :ok,
       else: {:error, :invalid_agent_token}
  end

  def verify(_, _), do: {:error, :invalid_agent_token}
end
