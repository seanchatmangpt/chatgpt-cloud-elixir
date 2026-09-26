defmodule ChatGPTCloud.Xaas.MixProject do
  use Mix.Project

  # Standalone client for the XaaS bounded runtime fabric (/internal-api/fabric).
  # Runtime closure is OTP only (:httpc, :ssl, :crypto, Elixir JSON); Bandit/Plug
  # exist solely to run the loopback contract fixture server in tests.
  def project do
    [
      app: :xaas_runtime_client,
      version: "26.9.25",
      elixir: "~> 1.18",
      elixirc_paths: elixirc_paths(Mix.env()),
      start_permanent: Mix.env() == :prod,
      deps: deps()
    ]
  end

  def application do
    [extra_applications: [:logger, :inets, :ssl, :crypto, :public_key]]
  end

  defp elixirc_paths(:test), do: ["lib", "test/support"]
  defp elixirc_paths(_), do: ["lib"]

  defp deps do
    [
      {:bandit, "1.12.5", only: :test},
      {:plug, "1.20.3", only: :test}
    ]
  end
end
