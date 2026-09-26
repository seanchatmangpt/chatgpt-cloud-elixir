defmodule ChatGPTCloudControlPlane.RuntimeContracts.ProducerSpoolIdentity do
  @moduledoc "Binds producer spool records to producer repo, exact SHA, protocol, and payload digest."

  def validate(%{producer_repo: repo, producer_sha: sha, protocol: protocol, payload_digest: digest})
      when is_binary(repo) and repo != "" and is_binary(sha) and sha != "" and
             protocol in ["ocel/2.0", "ggen/ecosystem/ocel/current"] and is_binary(digest) and digest != "", do: :ok

  def validate(_), do: {:error, :invalid_producer_spool_identity}
end
