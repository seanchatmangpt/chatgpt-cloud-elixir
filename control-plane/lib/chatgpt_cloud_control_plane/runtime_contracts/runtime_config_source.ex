defmodule ChatGPTCloudControlPlane.RuntimeContracts.RuntimeConfigSource do
  @moduledoc "Classifies runtime configuration sources and refuses credentials embedded in source control."

  def admit(%{kind: :secret, source: source}) when source in [:environment, :vault, :runtime_provider], do: :ok
  def admit(%{kind: :secret, source: :source}), do: {:error, :secret_in_source_refused}
  def admit(%{kind: :public, source: source}) when source in [:source, :environment, :runtime_provider], do: :ok
  def admit(_), do: {:error, :invalid_runtime_config_source}
end
