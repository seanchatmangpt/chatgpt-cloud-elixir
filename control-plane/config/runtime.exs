import Config

if System.get_env("PHX_SERVER") do
  config :chatgpt_cloud_control_plane, ChatGPTCloudWeb.Endpoint, server: true
end

config :chatgpt_cloud_control_plane, ChatGPTCloudWeb.Endpoint,
  http: [port: String.to_integer(System.get_env("PORT", "4000"))]

if config_env() == :prod do
  database_url =
    System.get_env("DATABASE_URL") ||
      raise "DATABASE_URL is required"

  uri = URI.parse(database_url)

  socket_options =
    cond do
      System.get_env("ECTO_IPV6") in ~w(true 1) -> [:inet6]
      is_binary(uri.host) and String.ends_with?(uri.host, ".internal") -> [:inet6]
      true -> []
    end

  config :chatgpt_cloud_control_plane, ChatGPTCloud.Repo,
    url: database_url,
    pool_size: String.to_integer(System.get_env("POOL_SIZE", "10")),
    socket_options: socket_options

  secret_key_base =
    System.get_env("SECRET_KEY_BASE") ||
      raise "SECRET_KEY_BASE is required"

  ingest_token =
    System.get_env("OCEL_INGEST_TOKEN") ||
      raise "OCEL_INGEST_TOKEN is required"

  admin_username =
    System.get_env("ADMIN_USERNAME") ||
      raise "ADMIN_USERNAME is required"

  admin_password =
    System.get_env("ADMIN_PASSWORD") ||
      raise "ADMIN_PASSWORD is required"

  host = System.get_env("PHX_HOST", "chatgpt-cloud-process-intelligence.fly.dev")

  config :chatgpt_cloud_control_plane,
    ocel_ingest_token: ingest_token,
    admin_username: admin_username,
    admin_password: admin_password,
    browser_auth_required: true

  config :chatgpt_cloud_control_plane, ChatGPTCloudWeb.Endpoint,
    url: [host: host, port: 443, scheme: "https"],
    http: [ip: {0, 0, 0, 0, 0, 0, 0, 0}],
    secret_key_base: secret_key_base
end
