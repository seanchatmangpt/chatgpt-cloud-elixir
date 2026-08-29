defmodule ChatGPTCloudControlPlane.RuntimeContracts.ActionIdempotencyKey do
  @moduledoc "Manufactures stable idempotency keys from action and exact subject identity."

  def build(action, repo, sha) when is_atom(action) and is_binary(repo) and repo != "" and is_binary(sha) and sha != "" do
    :crypto.hash(:sha256, Enum.join([Atom.to_string(action), repo, sha], ":")) |> Base.encode16(case: :lower)
  end

  def build(_, _, _), do: {:error, :invalid_idempotency_subject}
end
