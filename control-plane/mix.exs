defmodule ChatGPTCloud.MixProject do
  use Mix.Project

  def project do
    [
      app: :chatgpt_cloud_control_plane,
      version: "26.8.23",
      elixir: "~> 1.20",
      elixirc_paths: elixirc_paths(Mix.env()),
      start_permanent: Mix.env() == :prod,
      aliases: aliases(),
      deps: deps(),
      compilers: [:phoenix_live_view] ++ Mix.compilers()
    ]
  end

  def application do
    [
      mod: {ChatGPTCloud.Application, []},
      extra_applications: [:logger, :runtime_tools, :crypto]
    ]
  end

  def cli do
    [preferred_envs: [precommit: :test]]
  end

  defp elixirc_paths(:test), do: ["lib", "test/support"]
  defp elixirc_paths(_), do: ["lib"]

  defp deps do
    [
      {:ash, "3.32.0"},
      {:spark, "2.7.2"},
      {:reactor, "1.0.6"},
      {:igniter, "0.8.3", only: [:dev, :test]},
      {:ash_postgres, "2.12.0"},
      {:ash_phoenix, "2.3.24"},
      {:ash_json_api, "1.7.1"},
      {:ash_authentication, "5.0.0-rc.12"},
      {:ash_authentication_phoenix, "3.0.0-rc.9"},
      {:ash_oban, "0.8.13"},
      {:ash_state_machine, "0.2.13"},
      {:ash_archival, "2.0.3"},
      {:ash_money, "0.2.6"},
      {:ash_cloak, "0.3.1"},
      {:cloak, "~> 1.1"},
      {:ash_graphql, "1.10.1"},
      {:absinthe_plug, "~> 1.5"},
      {:ash_ai, "0.8.2"},
      {:ash_admin, "1.3.0"},
      {:bcrypt_elixir, "~> 3.0"},
      {:phoenix, "~> 1.8.9"},
      {:phoenix_ecto, "~> 4.7"},
      {:ecto_sql, "~> 3.13"},
      {:postgrex, ">= 0.0.0"},
      {:phoenix_html, "~> 4.1"},
      {:phoenix_live_reload, "~> 1.6", only: :dev},
      {:phoenix_live_view, "~> 1.2.8"},
      {:lazy_html, ">= 0.1.0", only: :test},
      {:esbuild, "~> 0.10", runtime: Mix.env() == :dev},
      {:tailwind, "~> 0.5", runtime: Mix.env() == :dev},
      {:heroicons,
       github: "tailwindlabs/heroicons",
       tag: "v2.2.0",
       sparse: "optimized",
       app: false,
       compile: false,
       depth: 1},
      {:daisyui,
       github: "saadeghi/daisyui",
       tag: "v5.5.20",
       sparse: "packages/bundle",
       app: false,
       compile: false,
       depth: 1},
      {:jason, "~> 1.4"},
      {:bandit, "~> 1.8"}
    ]
  end

  defp aliases do
    [
      setup: ["deps.get", "ecto.setup", "assets.setup", "assets.build"],
      "ecto.setup": ["ecto.create", "ecto.migrate"],
      "ecto.reset": ["ecto.drop", "ecto.setup"],
      test: ["ecto.create --quiet", "ecto.migrate --quiet", "test"],
      "assets.setup": ["tailwind.install --if-missing", "esbuild.install --if-missing"],
      "assets.build": [
        "compile",
        "tailwind chatgpt_cloud_control_plane",
        "esbuild chatgpt_cloud_control_plane"
      ],
      "assets.deploy": [
        "tailwind chatgpt_cloud_control_plane --minify",
        "esbuild chatgpt_cloud_control_plane --minify",
        "phx.digest"
      ],
      precommit: [
        "format --check-formatted",
        "compile --warnings-as-errors",
        "chatgpt_cloud.ecosystem.verify",
        "test"
      ]
    ]
  end
end
