import Config

config :logger, level: :info

config :chatgpt_cloud_control_plane, ChatGPTCloudWeb.Endpoint,
  cache_static_manifest: "priv/static/cache_manifest.json"
