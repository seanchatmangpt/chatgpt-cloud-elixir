defmodule ChatGPTCloudControlPlane.RuntimeContracts.GovernedAdapterPin do
  @moduledoc "Pins this consumer to the reusable GGen governed-runtime-adapter contract."

  @marketplace_sha "79969b97751c8da453d19437edcaa296780df15e"
  @pack "packs/governed-runtime-adapter-pack"

  def identity do
    %{repository: "seanchatmangpt/ggen-marketplace", sha: @marketplace_sha, pack: @pack, pi_owner: ["wasm4pm", "wasm4pm-compat"]}
  end

  def validate(%{repository: "seanchatmangpt/ggen-marketplace", sha: @marketplace_sha, pack: @pack}), do: :ok
  def validate(_), do: {:error, :governed_runtime_adapter_pin_mismatch}
end
