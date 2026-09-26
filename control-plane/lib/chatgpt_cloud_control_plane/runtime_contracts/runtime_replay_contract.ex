defmodule ChatGPTCloudControlPlane.RuntimeContracts.RuntimeReplayContract do
  @moduledoc "Requires replay to preserve subject, capsule, command, and configuration identities."

  @required ~w(subject_sha capsule_digest command config_digest)a

  def validate(replay) when is_map(replay) do
    case Enum.find(@required, &(Map.get(replay, &1) in [nil, ""])) do
      nil -> :ok
      field -> {:error, {:missing_replay_identity, field}}
    end
  end

  def validate(_), do: {:error, :invalid_runtime_replay_contract}
end
