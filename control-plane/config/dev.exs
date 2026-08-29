import Config

config :chatgpt_cloud_control_plane, ChatGPTCloud.Repo,
  username: System.get_env("PGUSER", "postgres"),
  password: System.get_env("PGPASSWORD", "postgres"),
  hostname: System.get_env("PGHOST", "localhost"),
  database: System.get_env("PGDATABASE", "chatgpt_cloud_control_plane_dev"),
  show_sensitive_data_on_connection_error: true,
  stacktrace: true,
  pool_size: 10

config :chatgpt_cloud_control_plane, ChatGPTCloudWeb.Endpoint,
  http: [ip: {127, 0, 0, 1}, port: String.to_integer(System.get_env("PORT", "4000"))],
  check_origin: false,
  code_reloader: true,
  debug_errors: true,
  secret_key_base: "n3P4g4x4sHfE4W6rR7hK1W3z3yW5wYf1oQ1lV4m8c4x7k8r9P4t6m7z8u9v0w1x2",
  watchers: [
    esbuild:
      {Esbuild, :install_and_run, [:chatgpt_cloud_control_plane, ~w(--sourcemap=inline --watch)]},
    tailwind: {Tailwind, :install_and_run, [:chatgpt_cloud_control_plane, ~w(--watch)]}
  ]

config :chatgpt_cloud_control_plane,
       :ocel_ingest_token,
       System.get_env("OCEL_INGEST_TOKEN", "dev-ocel-token")

# config.exs defaults browser_auth_required: true, but admin_username/admin_password
# are only ever set in config/runtime.exs under `if config_env() == :prod`. Without
# this, ChatGPTCloudWeb.AdminAuth's Application.fetch_env! crashes on every browser
# route in :dev. Mirror config/test.exs's local-dev pattern and disable browser auth.
config :chatgpt_cloud_control_plane, browser_auth_required: false
