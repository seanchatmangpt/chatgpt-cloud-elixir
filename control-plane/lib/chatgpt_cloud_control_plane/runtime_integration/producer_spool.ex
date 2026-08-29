defmodule ChatGPTCloud.RuntimeIntegration.ProducerSpool do
  @moduledoc "Keeps producer spooling observational and non-downgrading."

  @spec standing(atom(), :ok | {:error, term()}) :: atom()
  def standing(subject_standing, :ok), do: subject_standing
  def standing(subject_standing, {:error, _transport_error}), do: subject_standing
end
