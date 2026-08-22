defmodule ChatGPTCloudWeb.Endpoint do
  use Phoenix.Endpoint, otp_app: :chatgpt_cloud_control_plane

  @session_options [
    store: :cookie,
    key: "_chatgpt_cloud_control_plane_key",
    signing_salt: "3cR6K8Qn",
    same_site: "Lax"
  ]

  socket "/live", Phoenix.LiveView.Socket,
    websocket: [connect_info: [session: @session_options]],
    longpoll: [connect_info: [session: @session_options]]

  plug Plug.Static,
    at: "/",
    from: :chatgpt_cloud_control_plane,
    gzip: not code_reloading?,
    only: ChatGPTCloudWeb.static_paths(),
    raise_on_missing_only: code_reloading?

  if code_reloading? do
    socket "/phoenix/live_reload/socket", Phoenix.LiveReloader.Socket
    plug Phoenix.LiveReloader
    plug Phoenix.CodeReloader
    plug Phoenix.Ecto.CheckRepoStatus, otp_app: :chatgpt_cloud_control_plane
  end

  plug Plug.RequestId
  plug Plug.Telemetry, event_prefix: [:phoenix, :endpoint]

  plug Plug.Parsers,
    parsers: [:urlencoded, :multipart, :json],
    pass: ["*/*"],
    json_decoder: Phoenix.json_library()

  plug Plug.MethodOverride
  plug Plug.Head
  plug Plug.Session, @session_options
  plug ChatGPTCloudWeb.Router
end
