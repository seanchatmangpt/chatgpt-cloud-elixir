defmodule ChatGPTCloudControlPlane.RuntimeContracts.ReplayIdentity do
  @moduledoc "Binds replay to subject, command, config, and toolchain identities."
  @required ~w(subject_digest command_digest config_digest toolchain_digest)a
  def validate(map) when is_map(map) do
    if Enum.all?(@required, &(is_binary(Map.get(map, &1)) and byte_size(Map.get(map, &1)) >= 32)), do: :ok, else: {:error, :replay_identity_incomplete}
  end
  def validate(_), do: {:error, :invalid_replay_identity}
end
