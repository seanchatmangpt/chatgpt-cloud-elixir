defmodule ChatGPTCloud.RuntimeIntegration.ReplayContract do
  @moduledoc "Requires replay to bind the exact subject and verifier identities."
  @required [:subject_sha, :verifier_sha, :toolchain, :command]

  @spec validate(map()) :: :ok | {:error, {:missing_replay_field, atom()}}
  def validate(contract) when is_map(contract) do
    case Enum.find(@required, &(not Map.has_key?(contract, &1))) do
      nil -> :ok
      field -> {:error, {:missing_replay_field, field}}
    end
  end
end
