import Config

config :chatgpt_cloud_control_plane,
  namespace: ChatGPTCloud,
  ecto_repos: [ChatGPTCloud.Repo],
  ash_domains: [ChatGPTCloud.ProcessIntelligence],
  browser_auth_required: true

config :chatgpt_cloud_control_plane, ChatGPTCloud.Repo,
  migration_primary_key: [name: :id, type: :uuid],
  migration_foreign_key: [column: :id, type: :uuid]

config :chatgpt_cloud_control_plane, ChatGPTCloud.Vault,
  ciphers: [
    default: {
      Cloak.Ciphers.AES.GCM,
      tag: "AES.GCM.V1",
      key: :crypto.hash(:sha256, "chatgpt-cloud-control-plane-development-vault"),
      iv_length: 12
    }
  ]

config :chatgpt_cloud_control_plane, ChatGPTCloudWeb.Endpoint,
  url: [host: "localhost"],
  adapter: Bandit.PhoenixAdapter,
  render_errors: [
    formats: [html: ChatGPTCloudWeb.ErrorHTML, json: ChatGPTCloudWeb.ErrorJSON],
    layout: false
  ],
  pubsub_server: ChatGPTCloud.PubSub,
  live_view: [signing_salt: "7QJgB9c6"]

config :phoenix_live_view, root_tag_attribute: "phx-r"

config :esbuild,
  version: "0.25.9",
  chatgpt_cloud_control_plane: [
    args:
      ~w(js/app.js --bundle --target=es2022 --outdir=../priv/static/assets/js --external:/fonts/* --external:/images/* --alias:@=.),
    cd: Path.expand("../assets", __DIR__),
    env: %{"NODE_PATH" => [Path.expand("../deps", __DIR__), Mix.Project.build_path()]}
  ]

config :tailwind,
  version: "4.3.0",
  chatgpt_cloud_control_plane: [
    args: ~w(
      --input=assets/css/app.css
      --output=priv/static/assets/css/app.css
    ),
    cd: Path.expand("..", __DIR__),
    env: %{"NODE_PATH" => [Path.expand("../deps", __DIR__), Mix.Project.build_path()]}
  ]

config :logger, :default_formatter,
  format: "$time $metadata[$level] $message\n",
  metadata: [:request_id]

config :phoenix, :json_library, Jason

import_config "#{config_env()}.exs"
