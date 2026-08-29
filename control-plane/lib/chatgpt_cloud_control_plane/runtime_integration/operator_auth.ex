defmodule ChatGPTCloud.RuntimeIntegration.OperatorAuth do
  @moduledoc "Operator-session authentication boundary for browser control surfaces."

  @spec admit(map()) :: :ok | {:error, :operator_session_required}
  def admit(%{operator_id: id, authenticated: true}) when is_binary(id) and byte_size(id) > 0,
    do: :ok

  def admit(_), do: {:error, :operator_session_required}
end
