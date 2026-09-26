defmodule ChatGPTCloudControlPlane.RuntimeContracts.MigrationReceipt do
  @moduledoc "Binds database migration execution to exact schema version and subject SHA."

  def validate(%{schema_version: version, subject_sha: sha, exit: 0})
      when is_binary(version) and version != "" and is_binary(sha) and sha != "", do: :ok

  def validate(%{exit: exit}) when is_integer(exit), do: {:error, {:migration_failed, exit}}
  def validate(_), do: {:error, :invalid_migration_receipt}
end
