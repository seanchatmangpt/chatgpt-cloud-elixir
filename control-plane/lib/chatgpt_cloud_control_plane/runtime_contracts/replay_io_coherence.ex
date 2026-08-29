defmodule ChatGPTCloudControlPlane.RuntimeContracts.ReplayIoCoherence do
  @moduledoc "Requires replay input identity to match the original invocation and records output comparison explicitly."

  def validate(%{original_input: input, replay_input: input, original_output: original, replay_output: replay})
      when is_binary(input) and input != "" and is_binary(original) and is_binary(replay), do: {:ok, %{output_equal: original == replay}}

  def validate(_), do: {:error, :replay_io_mismatch}
end
