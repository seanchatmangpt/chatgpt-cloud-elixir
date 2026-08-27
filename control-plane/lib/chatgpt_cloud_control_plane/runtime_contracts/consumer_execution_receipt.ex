defmodule ChatGPTCloudControlPlane.RuntimeContracts.ConsumerExecutionReceipt do
  @moduledoc "Requires consumer-side execution evidence rather than build-workspace success alone."

  def validate(%{consumer: consumer, subject_sha: sha, command: command, exit: 0})
      when is_binary(consumer) and consumer != "" and is_binary(sha) and sha != "" and is_binary(command) and command != "", do: :ok

  def validate(%{exit: exit}) when is_integer(exit), do: {:error, {:consumer_execution_failed, exit}}
  def validate(_), do: {:error, :invalid_consumer_execution_receipt}
end
