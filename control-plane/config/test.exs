import Config

config :chatgpt_cloud_control_plane, ChatGPTCloud.Repo,
  url:
    System.get_env(
      "DATABASE_URL",
      "ecto://postgres:postgres@localhost/chatgpt_cloud_control_plane_test"
    ),
  pool: Ecto.Adapters.SQL.Sandbox,
  pool_size: 10

config :chatgpt_cloud_control_plane, ChatGPTCloudWeb.Endpoint,
  http: [ip: {127, 0, 0, 1}, port: 4002],
  url: [host: "127.0.0.1", port: 4002],
  secret_key_base: "6q6tmJgRZ1m3n5P7v9X2a4c6e8g0i2k4m6o8q0s2u4w6y8A0C2E4G6I8K0M2O4Q6",
  server: false

config :chatgpt_cloud_control_plane,
  browser_auth_required: false,
  ocel_ingest_token: "test-token"

config :logger, level: :warning
config :phoenix, :plug_init_mode, :runtime
