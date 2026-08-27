defmodule ChatGPTCloudControlPlane.RuntimeContracts.ReactorStepIdentity do
  @moduledoc "Binds Reactor steps to stable workflow, step, and exact-subject identities for replay."

  @required ~w(workflow step subject_sha)a

  def validate(step) when is_map(step) do
    case Enum.find(@required, &(Map.get(step, &1) in [nil, ""])) do
      nil -> :ok
      field -> {:error, {:missing_reactor_step_identity, field}}
    end
  end

  def validate(_), do: {:error, :invalid_reactor_step}
end
