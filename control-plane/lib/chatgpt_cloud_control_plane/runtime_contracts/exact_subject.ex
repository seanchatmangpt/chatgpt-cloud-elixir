defmodule ChatGPTCloudControlPlane.RuntimeContracts.ExactSubject do
  @moduledoc "Validates the immutable repo/ref/SHA identity required by runtime actions."

  @required ~w(repo ref sha)a

  def validate(subject) when is_map(subject) do
    case Enum.find(@required, &(blank?(Map.get(subject, &1)) and blank?(Map.get(subject, Atom.to_string(&1))))) do
      nil -> :ok
      field -> {:error, {:missing_subject_identity, field}}
    end
  end

  def validate(_), do: {:error, :invalid_subject}

  defp blank?(value), do: value in [nil, ""]
end
