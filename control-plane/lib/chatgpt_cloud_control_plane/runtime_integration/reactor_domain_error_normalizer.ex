defmodule ChatGPTCloud.RuntimeIntegration.ReactorDomainErrorNormalizer do
  @moduledoc "GGen-derived Reactor domain-error normalization boundary."

  def normalize(%Reactor.Error.Invalid{errors: errors} = original) do
    case Enum.find_value(errors, &domain_error/1) do
      nil -> {:reactor_failed, original}
      error -> error
    end
  end

  def normalize(other), do: {:reactor_failed, other}

  defp domain_error(%Reactor.Error.Invalid.RunStepError{error: error}), do: error
  defp domain_error(_), do: nil
end
