defmodule ChatGPTCloud.RuntimeIntegration.CapabilityAdmission do
  @moduledoc "Fail-closed admission for required runtime capabilities."

  @spec admit([atom()], [atom()]) :: :ok | {:error, {:missing_capabilities, [atom()]}}
  def admit(required, available) do
    missing = required -- available
    if missing == [], do: :ok, else: {:error, {:missing_capabilities, Enum.sort(missing)}}
  end
end
